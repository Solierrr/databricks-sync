from fastapi import APIRouter, Depends, Request
from starlette.responses import JSONResponse

from app.auth import require_sync_token
from app.config import load_config
from app.errors import ApiError, JobAlreadyRunning, SyncConfigurationError
from app.models import JobAccepted, JobStatus, SyncError, SyncResult
from gold_synchronizer import get_gold_configuration, synchronize_gold

router = APIRouter(tags=["Sincronização"], dependencies=[Depends(require_sync_token)])

UNAUTHENTICATED = {401: {"description": "Token Bearer ausente ou inválido"}}
ALREADY_RUNNING = {409: {"description": "Já existe uma sincronização em andamento"}}
FAILED_SYNC = {
    500: {
        "description": (
            "A sincronização terminou com erros ou houve erro inesperado; com erros de tabela, o campo `result` traz "
            "o resumo (`SyncResult`)"
        )
    }
}
NOT_CONFIGURED = {503: {"description": "O token da API ou as credenciais da sincronização não estão configurados"}}


def _final_result(job):
    if job.status == "completed":
        return JSONResponse(status_code=200, content=job.result)
    result = job.result
    if result is None:
        result = SyncResult(
            status="failed",
            tables_total=0,
            tables_synced=0,
            rows_synced=0,
            sources=[],
            errors=[SyncError(source="databricks", message=job.error or "unknown error")],
        ).model_dump()
    raise ApiError(500, "INTERNAL_ERROR", "A sincronização terminou com erros.", result=result)


@router.post(
    "/sync",
    response_model=JobAccepted,
    status_code=202,
    summary="Inicia a carga bronze do CoreDB no Databricks",
    description=(
        "Inicia a sincronização em segundo plano e devolve o id do job; acompanhe em `GET /sync/{job_id}`. "
        "No plano gratuito do Render a instância hiberna sem tráfego de entrada, então continue consultando o "
        "estado até o fim. Com `wait=true` a requisição espera o fim e responde com o resumo final (200) ou com o "
        "erro e o resumo em `result` (500). Só uma sincronização roda por vez."
    ),
    operation_id="startBronzeSync",
    responses={
        200: {"model": SyncResult, "description": "`wait=true`: a sincronização terminou"},
        **UNAUTHENTICATED,
        **ALREADY_RUNNING,
        **FAILED_SYNC,
        **NOT_CONFIGURED,
    },
    openapi_extra={
        "x-error-codes": ["UNAUTHENTICATED", "CONFLICT", "VALIDATION_FAILED", "INTERNAL_ERROR", "DEPENDENCY_UNAVAILABLE"]
    },
)
def trigger_sync(request: Request, wait: bool = False):
    try:
        config = load_config()
    except SyncConfigurationError as exc:
        raise ApiError(503, "DEPENDENCY_UNAVAILABLE", str(exc)) from exc

    jobs = request.app.state.jobs
    run = request.app.state.run_sync

    def runner(progress):
        return run(config, progress)

    try:
        if not wait:
            job = jobs.start(runner)
            return JobAccepted(id=job.id, status="running", status_url=f"/sync/{job.id}")
        job = jobs.run_blocking(runner)
    except JobAlreadyRunning as exc:
        raise ApiError(409, "CONFLICT", "Já existe uma sincronização em andamento.") from exc

    return _final_result(job)


@router.post(
    "/sync/gold",
    response_model=SyncResult,
    summary="Exporta os KPIs da camada gold para o AnalyticsDB",
    description=(
        "Exporta as views revisadas de `gold_export_manifest.json` e espera o fim. Chamado pelo job do "
        "`databricks-stocker` depois que a gold termina. Só uma sincronização roda por vez."
    ),
    operation_id="startGoldExport",
    responses={**UNAUTHENTICATED, **ALREADY_RUNNING, **FAILED_SYNC, **NOT_CONFIGURED},
    openapi_extra={"x-error-codes": ["UNAUTHENTICATED", "CONFLICT", "INTERNAL_ERROR", "DEPENDENCY_UNAVAILABLE"]},
)
def trigger_gold_sync(request: Request):
    try:
        get_gold_configuration()
    except SyncConfigurationError as exc:
        raise ApiError(503, "DEPENDENCY_UNAVAILABLE", str(exc)) from exc

    try:
        job = request.app.state.jobs.run_blocking(lambda _progress: synchronize_gold())
    except JobAlreadyRunning as exc:
        raise ApiError(409, "CONFLICT", "Já existe uma sincronização em andamento.") from exc
    return _final_result(job)


@router.get(
    "/sync/{job_id}",
    response_model=JobStatus,
    summary="Consulta o estado de um job de sincronização",
    description="O histórico fica só na memória da instância: os jobs somem quando ela reinicia.",
    operation_id="getSyncJob",
    responses={**UNAUTHENTICATED, 404: {"description": "Job não encontrado"}, **NOT_CONFIGURED},
    openapi_extra={"x-error-codes": ["UNAUTHENTICATED", "NOT_FOUND", "INTERNAL_ERROR", "DEPENDENCY_UNAVAILABLE"]},
)
def sync_status(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise ApiError(404, "NOT_FOUND", "Job não encontrado.")
    return JobStatus(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        progress=job.progress,
        result=SyncResult(**job.result) if job.result is not None else None,
        error=job.error,
    )
