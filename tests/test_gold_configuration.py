import json
from pathlib import Path

import pytest

from app.errors import SyncConfigurationError
from gold_synchronizer import get_gold_configuration

ENV = {
    "DATABRICKS_HOST": "https://dbx.example.com",
    "DATABRICKS_HTTP_PATH": "p",
    "DATABRICKS_TOKEN": "t",
    "DATABRICKS_CATALOG": "analytics",
    "DB_ANALYTICS_HOST": "h",
    "DB_ANALYTICS_PORT": "5432",
    "DB_ANALYTICS_USER": "u",
    "DB_ANALYTICS_PASS": "p",
    "DB_ANALYTICS_NAME": "analyticsdb",
}


@pytest.fixture
def env(monkeypatch):
    for name in ("DATABRICKS_SCHEMA_GOLD", "ANALYTICS_READER_ROLE", "GOLD_BATCH_SIZE"):
        monkeypatch.delenv(name, raising=False)
    for name, value in ENV.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


@pytest.mark.parametrize("catalog", ["analytics", "analyticsqa"])
def test_catalog_comes_from_the_environment(env, catalog):
    env.setenv("DATABRICKS_CATALOG", catalog)
    config = get_gold_configuration()
    assert config["catalog"] == catalog
    assert config["source_schema"] == "gold"


def test_catalog_is_required(env):
    env.delenv("DATABRICKS_CATALOG")
    with pytest.raises(SyncConfigurationError):
        get_gold_configuration()


def test_manifest_lists_the_english_kpi_tables_without_a_catalog():
    manifest = json.loads((Path(__file__).resolve().parents[1] / "gold_export_manifest.json").read_text())
    assert "catalog" not in manifest
    assert len(manifest["tables"]) == 19
    assert all(name.startswith("kpi_") for name in manifest["tables"])
    assert not any("fornecedor" in name or "demandante" in name or "profissional" in name for name in manifest["tables"])
    supplier = [n for n, rule in manifest["tables"].items() if rule["scope"] == "SUPPLIER"]
    assert all(n.startswith("kpi_supplier_") for n in supplier) and len(supplier) == 10
