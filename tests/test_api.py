import threading

import pytest
from fastapi.testclient import TestClient

from app.config import REQUIRED_VARIABLES
from app.errors import SyncExecutionError
from app.main import create_app
from app.services.jobs import JobManager
from app.version import VERSION

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


def client(run_sync=ok_runner, check_ready=lambda: True):
    return TestClient(create_app(JobManager(), run_sync, check_ready))


def test_health_needs_no_token():
    assert client().get("/health").json() == {"status": "UP", "version": VERSION}


def test_ready_is_up_when_the_dependencies_answer():
    response = client().get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_ready_is_down_when_a_dependency_fails():
    response = client(check_ready=lambda: False).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "DOWN"}


def assert_problem(response, status, error_code):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert body["type"] == "about:blank"
    assert body["title"] == error_code
    assert body["status"] == status
    assert body["errorCode"] == error_code
    assert body["detail"]
    assert body["instance"]
    assert body["timestamp"]
    return body


def test_sync_requires_the_bearer_token():
    body = assert_problem(client().post("/sync"), 401, "UNAUTHENTICATED")
    assert body["instance"] == "/sync"
    assert_problem(client().post("/sync", headers={"Authorization": "Bearer wrong"}), 401, "UNAUTHENTICATED")


def test_sync_answers_503_without_a_configured_token(monkeypatch):
    monkeypatch.delenv("SYNC_API_TOKEN")
    assert_problem(client().post("/sync", headers=HEADERS), 503, "DEPENDENCY_UNAVAILABLE")


def test_sync_answers_503_when_credentials_are_missing(monkeypatch):
    monkeypatch.delenv("DB_CORE_HOST")
    body = assert_problem(client().post("/sync", headers=HEADERS), 503, "DEPENDENCY_UNAVAILABLE")
    assert "DB_CORE_HOST" in body["detail"]


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
    assert_problem(client().get("/sync/missing", headers=HEADERS), 404, "NOT_FOUND")


def test_status_requires_the_token():
    assert client().get("/sync/anything").status_code == 401


def test_a_second_sync_is_rejected_while_one_runs():
    release = threading.Event()

    def slow(config, progress):
        release.wait(5)
        return ok_runner(config, progress)

    app_client = client(slow)
    assert app_client.post("/sync", headers=HEADERS).status_code == 202
    assert_problem(app_client.post("/sync", headers=HEADERS), 409, "CONFLICT")
    release.set()


def test_wait_returns_the_final_summary():
    response = client().post("/sync?wait=true", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_wait_returns_500_with_the_summary_when_tables_fail():
    def failing(config, progress):
        raise SyncExecutionError({"status": "failed", "tables_total": 1, "tables_synced": 0, "rows_synced": 0, "sources": [], "errors": [{"source": "DB_CORE", "message": "boom"}]})

    body = assert_problem(client(failing).post("/sync?wait=true", headers=HEADERS), 500, "INTERNAL_ERROR")
    assert body["result"]["errors"][0]["message"] == "boom"


def test_wait_returns_500_for_unexpected_errors():
    def exploding(config, progress):
        raise RuntimeError("unexpected")

    body = assert_problem(client(exploding).post("/sync?wait=true", headers=HEADERS), 500, "INTERNAL_ERROR")
    assert body["result"]["errors"][0]["message"] == "unexpected"


def test_invalid_query_parameter_is_a_validation_problem():
    body = assert_problem(client().post("/sync?wait=maybe", headers=HEADERS), 422, "VALIDATION_FAILED")
    assert body["errors"][0]["field"] == "wait"
    assert body["errors"][0]["errorCode"] == "VALIDATION_FAILED"


def test_unknown_route_is_a_not_found_problem():
    assert_problem(client().get("/missing"), 404, "NOT_FOUND")
