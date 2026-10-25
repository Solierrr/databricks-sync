from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models import HealthStatus, ReadinessStatus
from app.version import VERSION

router = APIRouter(tags=["Saúde"])


@router.get(
    "/health",
    response_model=HealthStatus,
    summary="Indica se o processo está vivo",
    description="Não consulta os bancos nem o Databricks.",
    operation_id="getHealth",
    openapi_extra={"security": []},
)
def health() -> HealthStatus:
    return HealthStatus(status="UP", version=VERSION)


@router.get(
    "/ready",
    response_model=ReadinessStatus,
    summary="Indica se o serviço está pronto para atender",
    description=(
        "Confere, com timeout de 2 segundos cada, se o CoreDB, o AnalyticsDB (quando configurado) e o workspace do "
        "Databricks estão alcançáveis. A checagem do Databricks usa a API REST do workspace e não liga o SQL "
        "Warehouse. Responde 503 com `{\"status\": \"DOWN\"}` quando alguma dependência está fora do ar."
    ),
    operation_id="getReady",
    openapi_extra={"security": []},
)
def ready(request: Request) -> JSONResponse:
    if request.app.state.check_ready():
        return JSONResponse({"status": "UP"})
    return JSONResponse({"status": "DOWN"}, status_code=503)
