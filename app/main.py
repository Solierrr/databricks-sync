import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import load_env_file
from app.errors import register_error_handlers
from app.infra.readiness import check_dependencies
from app.openapi import install_openapi
from app.routes import health, sync
from app.services.jobs import JobManager
from app.services.sync_service import synchronize
from app.version import VERSION

DESCRIPTION = (
    "Envia o CoreDB para a camada bronze do Databricks (`POST /sync`) e exporta os KPIs já materializados na "
    "camada gold para o AnalyticsDB (`POST /sync/gold`). É acionado à mão e pelo job do `databricks-stocker`, "
    "sem horário fixo. Autentique com o token de serviço `SYNC_API_TOKEN` no cabeçalho "
    "`Authorization: Bearer <token>`."
)

TAGS = [
    {"name": "Saúde", "description": "Vivo e pronto do serviço, sem autenticação"},
    {"name": "Sincronização", "description": "Carga bronze no Databricks e exportação gold para o AnalyticsDB"},
]


def create_app(jobs: JobManager | None = None, run_sync=synchronize, check_ready=check_dependencies) -> FastAPI:
    load_env_file()
    logging.basicConfig(level=logging.INFO)

    docs_enabled = os.environ.get("DOCS_ENABLED", "true").lower() != "false"
    app = FastAPI(
        title="Solaria — databricks-sync",
        description=DESCRIPTION,
        version=VERSION,
        contact={"name": "Solaria", "url": "https://github.com/Solierrr"},
        license_info={"name": "CC0-1.0", "url": "https://creativecommons.org/publicdomain/zero/1.0/"},
        servers=[
            {"url": "https://databricks.solarianetwork.site", "description": "Render"},
            {"url": "http://localhost:8000", "description": "Local"},
        ],
        openapi_tags=TAGS,
        docs_url="/docs" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        redoc_url=None,
        swagger_ui_parameters={
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "tryItOutEnabled": True,
            "tagsSorter": "alpha",
            "operationsSorter": "alpha",
        },
    )
    origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    install_openapi(app)
    app.state.jobs = jobs or JobManager()
    app.state.run_sync = run_sync
    app.state.check_ready = check_ready
    app.include_router(health.router)
    app.include_router(sync.router)
    return app


app = create_app()
