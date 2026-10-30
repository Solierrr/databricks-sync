from app.config import REQUIRED_VARIABLES
from app.infra import readiness

ENVIRON = {name: "x" for name in REQUIRED_VARIABLES}


def test_not_ready_without_the_sync_configuration():
    assert readiness.check_dependencies({}) is False


def test_ready_pings_databricks_and_every_configured_database(monkeypatch):
    pinged = []
    monkeypatch.setattr(readiness, "ping_databricks", lambda host, http_path, token: pinged.append("databricks"))
    monkeypatch.setattr(readiness, "ping_postgres", lambda prefix, environ: pinged.append(prefix))

    assert readiness.check_dependencies({**ENVIRON, "DB_ANALYTICS_HOST": "x"}) is True
    assert sorted(pinged) == ["DB_ANALYTICS", "DB_CORE", "databricks"]


def test_not_ready_when_a_dependency_fails(monkeypatch):
    def unreachable(*args):
        raise OSError("timeout")

    monkeypatch.setattr(readiness, "ping_databricks", lambda host, http_path, token: None)
    monkeypatch.setattr(readiness, "ping_postgres", unreachable)

    assert readiness.check_dependencies(ENVIRON) is False
