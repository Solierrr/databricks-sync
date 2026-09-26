import hmac
import os
from threading import Lock
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from synchronizer import SyncConfigurationError, SyncExecutionError, synchronize

app = FastAPI(title="Databricks Bronze Sync", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=False)
sync_lock = Lock()


class SyncError(BaseModel):
    source: str
    dbx_schema: str | None = None
    table: str | None = None
    message: str


class SourceSyncResult(BaseModel):
    source: str
    dbx_schema: str
    tables_total: int
    tables_synced: int
    rows_synced: int
    errors: list[SyncError] = Field(default_factory=list)


class SyncResult(BaseModel):
    status: Literal["completed", "failed"]
    tables_total: int
    tables_synced: int
    rows_synced: int
    sources: list[SourceSyncResult]
    errors: list[SyncError] = Field(default_factory=list)


def require_sync_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> None:
    expected_token = os.environ.get("SYNC_API_TOKEN", "")
    if not expected_token:
        raise HTTPException(status_code=503, detail="SYNC_API_TOKEN is not configured")
    if credentials is None or not hmac.compare_digest(credentials.credentials, expected_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@app.post(
    "/sync",
    response_model=SyncResult,
    responses={
        401: {"description": "Bearer token is missing or invalid"},
        409: {"description": "A synchronization is already running"},
        500: {"model": SyncResult, "description": "The synchronization completed with errors"},
        503: {"description": "The API token or sync credentials are not configured"},
    },
)
def trigger_sync(_: None = Depends(require_sync_token)):
    if not sync_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A synchronization is already running")

    try:
        try:
            return synchronize()
        except SyncConfigurationError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except SyncExecutionError as exc:
            return JSONResponse(status_code=500, content=exc.summary)
        except Exception as exc:
            result = SyncResult(
                status="failed",
                tables_total=0,
                tables_synced=0,
                rows_synced=0,
                sources=[],
                errors=[SyncError(source="databricks", message=str(exc))],
            )
            return JSONResponse(status_code=500, content=result.model_dump())
    finally:
        sync_lock.release()
