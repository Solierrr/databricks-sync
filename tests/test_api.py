import threading

import pytest
from fastapi.testclient import TestClient

from app.config import REQUIRED_VARIABLES
from app.errors import SyncExecutionError
from app.main import create_app
from app.services.jobs import JobManager

HEADERS = {"Authorization": "Bearer secret-token"}


@pytest.fixture(autouse=True)
def environment(monkeypatch):
    for name in REQUIRED_VARIABLES:
        monkeypatch.setenv(name, "x")
    monkeypatch.setenv("SYNC_API_TOKEN", "secret-token")


def ok_runner(config, progress):
    progress({"event": "source_started", "source": "DB_CORE", "tables": 1})
    progress({"event": "table_synced", "source": "DB_CORE", "table": "a", "rows": 3})
    return {
        "status": "completed",
        "tables_total": 1,
        "tables_synced": 1,
        "rows_synced": 3,
        "sources": [
            {"source": "DB_CORE", "dbx_schema": "bronze_core", "tables_total": 1, "tables_synced": 1, "rows_synced": 3, "errors": []}
        ],
        "errors": [],
    }


def client(run_sync=ok_runner):
    return TestClient(create_app(JobManager(), run_sync))


def test_health_needs_no_token():
    assert client().get("/health").json() == {"status": "ok"}


def test_sync_requires_the_bearer_token():
    assert client().post("/sync").status_code == 401
    assert client().post("/sync", headers={"Authorization": "Bearer wrong"}).status_code == 401


def test_sync_answers_503_without_a_configured_token(monkeypatch):
    monkeypatch.delenv("SYNC_API_TOKEN")
    assert client().post("/sync", headers=HEADERS).status_code == 503


def test_sync_answers_503_when_credentials_are_missing(monkeypatch):
    monkeypatch.delenv("DB_CORE_HOST")
    response = client().post("/sync", headers=HEADERS)
    assert response.status_code == 503
    assert "DB_CORE_HOST" in response.json()["detail"]


def test_sync_starts_a_job_and_the_status_endpoint_reports_it():
    app_client = client()

    accepted = app_client.post("/sync", headers=HEADERS)
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "running"
    assert body["status_url"] == f"/sync/{body['id']}"

    status = None
    for _ in range(100):
        status = app_client.get(body["status_url"], headers=HEADERS).json()
        if status["status"] != "running":
            break
        threading.Event().wait(0.05)
    assert status["status"] == "completed"
    assert status["result"]["rows_synced"] == 3
    assert status["progress"]["tables_synced"] == 1


def test_status_of_an_unknown_job_is_404():
    assert client().get("/sync/missing", headers=HEADERS).status_code == 404


def test_status_requires_the_token():
    assert client().get("/sync/anything").status_code == 401


def test_a_second_sync_is_rejected_while_one_runs():
    release = threading.Event()

    def slow(config, progress):
        release.wait(5)
        return ok_runner(config, progress)

    app_client = client(slow)
    assert app_client.post("/sync", headers=HEADERS).status_code == 202
    assert app_client.post("/sync", headers=HEADERS).status_code == 409
    release.set()


def test_wait_returns_the_final_summary():
    response = client().post("/sync?wait=true", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_wait_returns_500_with_the_summary_when_tables_fail():
    def failing(config, progress):
        raise SyncExecutionError({"status": "failed", "tables_total": 1, "tables_synced": 0, "rows_synced": 0, "sources": [], "errors": [{"source": "DB_CORE", "message": "boom"}]})

    response = client(failing).post("/sync?wait=true", headers=HEADERS)
    assert response.status_code == 500
    assert response.json()["errors"][0]["message"] == "boom"


def test_wait_returns_500_for_unexpected_errors():
    def exploding(config, progress):
        raise RuntimeError("unexpected")

    response = client(exploding).post("/sync?wait=true", headers=HEADERS)
    assert response.status_code == 500
    assert response.json()["errors"][0]["message"] == "unexpected"
