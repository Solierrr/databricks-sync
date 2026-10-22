import pytest

from app.config import REQUIRED_VARIABLES, load_config
from app.errors import SyncConfigurationError


def full_env(**overrides):
    env = {name: "x" for name in REQUIRED_VARIABLES}
    env["DATABRICKS_HOST"] = "https://dbx.example.com"
    env.update(overrides)
    return env


def test_reports_every_missing_variable():
    env = full_env()
    del env["DB_CORE_HOST"]
    del env["DATABRICKS_TOKEN"]
    with pytest.raises(SyncConfigurationError) as error:
        load_config(env)
    assert "DB_CORE_HOST" in str(error.value)
    assert "DATABRICKS_TOKEN" in str(error.value)


def test_builds_core_source_with_default_schema():
    config = load_config(full_env())
    assert config.dbx_host == "dbx.example.com"
    assert [(s.env_prefix, s.dbx_schema) for s in config.sources] == [
        ("DB_CORE", "bronze_core"),
    ]
    assert config.batch_size == 500


@pytest.mark.parametrize("value", ["0", "-5", "many"])
def test_rejects_invalid_batch_size(value):
    env = full_env(SYNC_BATCH_SIZE=value)
    with pytest.raises(SyncConfigurationError):
        load_config(env)


def test_accepts_custom_batch_size():
    assert load_config(full_env(SYNC_BATCH_SIZE="50")).batch_size == 50
