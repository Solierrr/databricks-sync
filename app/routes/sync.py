from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from app.auth import require_sync_token
from app.config import load_config
from app.errors import JobAlreadyRunning, SyncConfigurationError
from app.models import JobAccepted, JobStatus, SyncError, SyncResult
from gold_synchronizer import get_gold_configuration, synchronize_gold

router = APIRouter(tags=["sync"], dependencies=[Depends(require_sync_token)])


def _final_result(job):
    if job.status == "completed":
        return JSONResponse(status_code=200, content=job.result)
    if job.result is not None:
        return JSONResponse(status_code=500, content=job.result)
    failure = SyncResult(
        status="failed",
        tables_total=0,
        tables_synced=0,
        rows_synced=0,
        sources=[],
        errors=[SyncError(source="databricks", message=job.error or "unknown error")],
    )
    return JSONResponse(status_code=500, content=failure.model_dump())


@router.post(
    "/sync",
    response_model=JobAccepted,
    status_code=202,
    summary="Start the bronze synchronization",
    description=(
        "Starts the synchronization in the background and returns the job id; follow it in `GET /sync/{id}`. "
        "On the free Render plan the instance sleeps without inbound traffic, so keep polling the status until it "
        "finishes. With `wait=true` the request blocks until the end and answers with the final summary (200 or 500)."
    ),
    responses={
        200: {"model": SyncResult, "description": "`wait=true`: the synchronization finished"},
        401: {"description": "Bearer token is missing or invalid"},
        409: {"description": "A synchronization is already running"},
        500: {"model": SyncResult, "description": "`wait=true`: the synchronization completed with errors"},
        503: {"description": "The API token or sync credentials are not configured"},
    },
)
def trigger_sync(request: Request, wait: bool = False):
    try:
        config = load_config()
    except SyncConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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
        raise HTTPException(status_code=409, detail="A synchronization is already running") from exc

    return _final_result(job)


@router.post(
    "/sync/gold",
    response_model=SyncResult,
    summary="Export Gold KPIs to AnalyticsDB",
    responses={
        401: {"description": "Bearer token is missing or invalid"},
        409: {"description": "A synchronization is already running"},
        500: {"model": SyncResult, "description": "The Gold export completed with errors"},
        503: {"description": "The API token or Gold credentials are not configured"},
    },
)
def trigger_gold_sync(request: Request):
    try:
        get_gold_configuration()
    except SyncConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    try:
        job = request.app.state.jobs.run_blocking(lambda _progress: synchronize_gold())
    except JobAlreadyRunning as exc:
        raise HTTPException(status_code=409, detail="A synchronization is already running") from exc
    return _final_result(job)


@router.get(
    "/sync/{job_id}",
    response_model=JobStatus,
    summary="Status of a synchronization job",
    responses={401: {"description": "Bearer token is missing or invalid"}, 404: {"description": "Unknown job id"}},
)
def sync_status(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(
        id=job.id,
        status=job.status,
        created_at=job.created_at,
        finished_at=job.finished_at,
        progress=job.progress,
        result=SyncResult(**job.result) if job.result is not None else None,
        error=job.error,
    )
