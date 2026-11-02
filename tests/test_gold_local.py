import json
from datetime import date, datetime
from decimal import Decimal

import pytest

import gold_synchronizer as gold
from app.errors import SyncConfigurationError


def _data():
    return {
        "schemas": {
            "kpi_supplier_stock_summary": [
                ["supplier_id", "string"],
                ["stock_units", "bigint"],
                ["avg_price", "decimal(18,2)"],
                ["reference_date", "date"],
                ["updated_at", "timestamp"],
            ]
        },
        "tables": {
            "kpi_supplier_stock_summary": [
                {
                    "supplier_id": "s1",
                    "stock_units": 4,
                    "avg_price": "12.50",
                    "reference_date": "2026-11-02",
                    "updated_at": "2026-11-02T10:00:00",
                },
                {
                    "supplier_id": "s2",
                    "stock_units": 0,
                    "avg_price": None,
                    "reference_date": None,
                    "updated_at": None,
                },
            ]
        },
    }


RULE = {"scope": "SUPPLIER", "id_column": "supplier_id"}
TABLE = "kpi_supplier_stock_summary"


def test_columns_map_spark_types_to_postgres():
    columns = gold._local_columns(_data(), TABLE, RULE)
    assert columns == [
        ("supplier_id", "text"),
        ("stock_units", "bigint"),
        ("avg_price", "numeric(18,2)"),
        ("reference_date", "date"),
        ("updated_at", "timestamp with time zone"),
    ]


def test_rows_keep_exact_decimals_and_typed_dates():
    data = _data()
    columns = gold._local_columns(data, TABLE, RULE)
    [batch] = list(gold._local_batches(data, {"batch_size": 10}, TABLE, columns))
    assert batch[0] == (
        "s1",
        4,
        Decimal("12.50"),
        date(2026, 11, 2),
        datetime.fromisoformat("2026-11-02T10:00:00"),
    )
    assert batch[1] == ("s2", 0, None, None, None)


def test_batches_respect_the_batch_size():
    data = _data()
    columns = gold._local_columns(data, TABLE, RULE)
    batches = list(gold._local_batches(data, {"batch_size": 1}, TABLE, columns))
    assert [len(b) for b in batches] == [1, 1]


def test_missing_column_types_ask_for_a_new_pipeline_run():
    data = _data()
    del data["schemas"][TABLE]
    with pytest.raises(SyncConfigurationError, match="run the pipeline again"):
        gold._local_columns(data, TABLE, RULE)


def test_scope_column_must_exist():
    with pytest.raises(SyncConfigurationError, match="does not contain"):
        gold._local_columns(
            _data(), TABLE, {"scope": "SUPPLIER", "id_column": "requester_id"}
        )


def test_unknown_spark_type_is_refused():
    data = _data()
    data["schemas"][TABLE][1][1] = "array<string>"
    with pytest.raises(SyncConfigurationError, match="Unsupported"):
        gold._local_columns(data, TABLE, RULE)


def test_manifest_matches_the_stocker_contract():
    manifest = json.loads(
        gold.ROOT.joinpath("gold_export_manifest.json").read_text(encoding="utf-8")
    )
    assert (manifest["catalog"], manifest["schema"]) == ("analytics", "gold")
    assert len(manifest["tables"]) == 19
    scopes = {rule["scope"] for rule in manifest["tables"].values()}
    assert scopes == {"ADMIN", "SUPPLIER", "REQUESTER", "PROFESSIONAL"}
