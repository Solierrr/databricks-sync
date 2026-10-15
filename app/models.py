from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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


class JobProgress(BaseModel):
    current_source: str | None = None
    tables_total: int = 0
    tables_synced: int = 0
    tables_failed: int = 0
    rows_synced: int = 0


class JobAccepted(BaseModel):
    id: str
    status: Literal["running"]
    status_url: str


class JobStatus(BaseModel):
    id: str
    status: Literal["running", "completed", "failed"]
    created_at: datetime
    finished_at: datetime | None = None
    progress: JobProgress
    result: SyncResult | None = None
    error: str | None = None
