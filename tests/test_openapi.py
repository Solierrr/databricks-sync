from fastapi.testclient import TestClient

from app.main import create_app
from app.services.jobs import JobManager
from app.version import VERSION


def contract():
    return TestClient(create_app(JobManager())).get("/openapi.json").json()


def test_contract_metadata_follows_the_standard():
    info = contract()["info"]
    assert info["title"] == "Solaria — databricks-sync"
    assert info["version"] == VERSION
    assert info["contact"] == {"name": "Solaria", "url": "https://github.com/Solierrr"}
    assert info["license"]["name"] == "CC0-1.0"


def test_contract_declares_the_bearer_scheme_by_default():
    schema = contract()
    assert schema["security"] == [{"bearerAuth": []}]
    assert schema["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"
    assert schema["paths"]["/health"]["get"]["security"] == []
    assert schema["paths"]["/ready"]["get"]["security"] == []


def test_every_error_response_uses_problem_detail():
    schema = contract()
    assert "ProblemDetail" in schema["components"]["schemas"]
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    for path in schema["paths"].values():
        for operation in path.values():
            assert operation["operationId"]
            assert operation["summary"]
            assert "500" in operation["responses"]
            for code, response in operation["responses"].items():
                if code.startswith(("4", "5")):
                    assert list(response["content"]) == ["application/problem+json"]


def test_docs_can_be_turned_off(monkeypatch):
    monkeypatch.setenv("DOCS_ENABLED", "false")
    app_client = TestClient(create_app(JobManager()))
    assert app_client.get("/openapi.json").status_code == 404
    assert app_client.get("/docs").status_code == 404
