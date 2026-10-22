import logging

from fastapi import FastAPI

from app.config import load_env_file
from app.routes import health, sync
from app.services.jobs import JobManager
from app.services.sync_service import synchronize


def create_app(jobs: JobManager | None = None, run_sync=synchronize) -> FastAPI:
    load_env_file()
    logging.basicConfig(level=logging.INFO)

    app = FastAPI(title="Databricks Medallion Sync", version="1.1.0")
    app.state.jobs = jobs or JobManager()
    app.state.run_sync = run_sync
    app.include_router(health.router)
    app.include_router(sync.router)
    return app


app = create_app()
