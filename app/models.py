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


class ProblemFieldError(BaseModel):
    field: str = Field(description="Campo inválido", examples=["wait"])
    errorCode: str = Field(description="Código estável do erro do campo", examples=["VALIDATION_FAILED"])
    detail: str = Field(description="Explicação para quem depura", examples=["Input should be a valid boolean"])


class ProblemDetail(BaseModel):
    type: str = Field(description="Sempre about:blank", examples=["about:blank"])
    title: str = Field(description="O mesmo valor de errorCode", examples=["CONFLICT"])
    status: int = Field(description="Código HTTP", examples=[409])
    errorCode: str = Field(description="Código estável do catálogo de erros", examples=["CONFLICT"])
    detail: str = Field(description="Explicação para quem depura; o front não exibe", examples=["Já existe uma sincronização em andamento."])
    instance: str = Field(description="Caminho da requisição", examples=["/sync"])
    timestamp: datetime = Field(description="Momento do erro em UTC")
    traceId: str | None = Field(default=None, description="Id do trace, quando houver")
    errors: list[ProblemFieldError] | None = Field(default=None, description="Erros por campo, só em validação")


class HealthStatus(BaseModel):
    status: Literal["UP"] = Field(examples=["UP"])
    version: str = Field(examples=["0.2.0"])


class ReadinessStatus(BaseModel):
    status: Literal["UP", "DOWN"] = Field(examples=["UP"])
