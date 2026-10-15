import pytest

from app.config import SourceConfig, SyncConfig
from app.errors import SyncExecutionError
from app.services.sync_service import sync_source, sync_table, synchronize
from tests.fakes import FakeDbxConnection, FakeDbxCursor, FakeSource


def test_sync_table_recreates_the_table_and_inserts_in_batches():
    cursor = FakeDbxCursor()
    source = FakeSource({"users": [(1, "a"), (2, "b"), (3, "c")]})

    rows = sync_table(source, cursor, "cat", "bronze_core", "users", batch_size=2)

    assert rows == 3
    assert cursor.statements[0] == "CREATE OR REPLACE TABLE `cat`.`bronze_core`.`users` (`id` INT, `name` STRING)"
    assert [len(batch) for batch in cursor.batches] == [2, 1]
    assert "INSERT INTO `cat`.`bronze_core`.`users` (`id`, `name`) VALUES (?, ?)" in cursor.statements


def test_sync_table_with_no_rows_creates_the_table_only():
    cursor = FakeDbxCursor()

    assert sync_table(FakeSource({"empty": []}), cursor, "cat", "s", "empty", batch_size=10) == 0
    assert cursor.batches == []


def test_sync_source_collects_failures_and_keeps_going():
    cursor = FakeDbxCursor()
    source = FakeSource({"good": [(1, "a")], "bad": "boom", "other": [(2, "b"), (3, "c")]})
    events = []

    result = sync_source(
        FakeDbxConnection(cursor), lambda prefix: source, "cat", SourceConfig("DB_CORE", "bronze_core"), 10, events.append
    )

    assert result["tables_total"] == 3
    assert result["tables_synced"] == 2
    assert result["rows_synced"] == 3
    assert [error["table"] for error in result["errors"]] == ["bad"]
    assert source.rolled_back == 1
    assert source.closed
    assert [event["event"] for event in events] == ["source_started", "table_synced", "table_failed", "table_synced"]


def make_config():
    return SyncConfig("h", "p", "t", "cat", (SourceConfig("DB_CORE", "bronze_core"), SourceConfig("DB_AUTH", "bronze_auth")))


def test_synchronize_returns_the_summary_when_everything_works():
    cursor = FakeDbxCursor()
    sources = {"DB_CORE": FakeSource({"a": [(1, "x")]}), "DB_AUTH": FakeSource({"b": [(2, "y")]})}

    summary = synchronize(make_config(), lambda prefix: sources[prefix], lambda config: FakeDbxConnection(cursor))

    assert summary["status"] == "completed"
    assert summary["tables_total"] == 2
    assert summary["rows_synced"] == 2


def test_synchronize_raises_with_the_summary_when_a_source_fails():
    cursor = FakeDbxCursor()
    cursor.fail_on = "CREATE SCHEMA"

    def factory(prefix):
        return FakeSource({"a": [(1, "x")]})

    with pytest.raises(SyncExecutionError) as error:
        synchronize(make_config(), factory, lambda config: FakeDbxConnection(cursor))

    summary = error.value.summary
    assert summary["status"] == "failed"
    assert {item["source"] for item in summary["errors"]} == {"DB_CORE", "DB_AUTH"}
