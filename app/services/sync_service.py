import logging
from collections.abc import Callable
from typing import Any

from app.config import SourceConfig, SyncConfig
from app.errors import SyncExecutionError
from app.infra import databricks as databricks_infra
from app.infra.postgres import PostgresSource
from app.infra.typemap import sql_type_for, to_dbx_value

logger = logging.getLogger(__name__)

Progress = Callable[[dict], None]


def _ignore(_: dict) -> None:
    return None


def sync_table(source, dbx_cur, dbx_catalog: str, dbx_schema: str, table: str, batch_size: int) -> int:
    columns = source.columns(table)
    col_names = [column[0] for column in columns]
    col_defs = ", ".join(
        f"`{name}` {sql_type_for(pg_type, precision, scale)}" for name, pg_type, precision, scale in columns
    )

    full_name = f"`{dbx_catalog}`.`{dbx_schema}`.`{table}`"
    dbx_cur.execute(f"CREATE OR REPLACE TABLE {full_name} ({col_defs})")

    placeholders = ", ".join(["?"] * len(col_names))
    col_list = ", ".join(f"`{name}`" for name in col_names)
    insert_sql = f"INSERT INTO {full_name} ({col_list}) VALUES ({placeholders})"

    total = 0
    for batch in source.rows(table, col_names, batch_size):
        dbx_cur.executemany(insert_sql, [tuple(to_dbx_value(value) for value in row) for row in batch])
        total += len(batch)
    return total


def sync_source(
    dbx_conn,
    source_factory: Callable[[str], Any],
    dbx_catalog: str,
    source_config: SourceConfig,
    batch_size: int,
    progress: Progress = _ignore,
) -> dict:
    env_prefix = source_config.env_prefix
    dbx_schema = source_config.dbx_schema
    source = source_factory(env_prefix)
    dbx_cur = dbx_conn.cursor()
    results = []
    errors = []

    try:
        dbx_cur.execute(f"CREATE SCHEMA IF NOT EXISTS `{dbx_catalog}`.`{dbx_schema}`")
        tables = source.tables()
        logger.info("Synchronizing %d tables from %s to %s.%s", len(tables), env_prefix, dbx_catalog, dbx_schema)
        progress({"event": "source_started", "source": env_prefix, "tables": len(tables)})

        for table in tables:
            try:
                row_count = sync_table(source, dbx_cur, dbx_catalog, dbx_schema, table, batch_size)
                results.append({"table": table, "rows_synced": row_count})
                progress({"event": "table_synced", "source": env_prefix, "table": table, "rows": row_count})
                logger.info("  ok  %s: %d rows", table, row_count)
            except Exception as exc:
                message = str(exc)
                try:
                    source.rollback()
                except Exception as rollback_exc:
                    message = f"{message}; Postgres rollback failed: {rollback_exc}"
                errors.append({"source": env_prefix, "dbx_schema": dbx_schema, "table": table, "message": message})
                progress({"event": "table_failed", "source": env_prefix, "table": table})
                logger.error("  FAILED %s: %s", table, message)

        return {
            "source": env_prefix,
            "dbx_schema": dbx_schema,
            "tables_total": len(tables),
            "tables_synced": len(results),
            "rows_synced": sum(result["rows_synced"] for result in results),
            "errors": errors,
        }
    finally:
        dbx_cur.close()
        source.close()


def synchronize(
    config: SyncConfig,
    source_factory: Callable[[str], Any] = PostgresSource.connect,
    dbx_connect: Callable[[SyncConfig], Any] = databricks_infra.connect,
    progress: Progress = _ignore,
) -> dict:
    source_results = []
    errors = []

    with dbx_connect(config) as dbx_conn:
        for source_config in config.sources:
            try:
                result = sync_source(
                    dbx_conn, source_factory, config.dbx_catalog, source_config, config.batch_size, progress
                )
                source_results.append(result)
                errors.extend(result["errors"])
            except Exception as exc:
                errors.append(
                    {
                        "source": source_config.env_prefix,
                        "dbx_schema": source_config.dbx_schema,
                        "table": None,
                        "message": str(exc),
                    }
                )

    summary = {
        "status": "failed" if errors else "completed",
        "tables_total": sum(result["tables_total"] for result in source_results),
        "tables_synced": sum(result["tables_synced"] for result in source_results),
        "rows_synced": sum(result["rows_synced"] for result in source_results),
        "sources": source_results,
        "errors": errors,
    }
    if errors:
        raise SyncExecutionError(summary)
    return summary
