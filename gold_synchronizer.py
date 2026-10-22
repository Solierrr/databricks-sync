"""Export the materialized workspace.gold_core KPIs into analyticsdb."""

import json
import os
import re
import sys
from contextlib import closing
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg2
from databricks import sql as dbsql
from psycopg2 import sql
from psycopg2.extras import execute_values

from synchronizer import SyncConfigurationError, SyncExecutionError


ROOT = Path(__file__).resolve().parent
IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
DECIMAL = re.compile(r"^DECIMAL\((\d+)\s*,\s*(\d+)\)$", re.IGNORECASE)
TEXT_TYPE = re.compile(r"^(?:VARCHAR|CHAR)\(\d+\)$", re.IGNORECASE)
TYPE_MAP = {
    "STRING": "text",
    "BOOLEAN": "boolean",
    "TINYINT": "smallint",
    "SMALLINT": "smallint",
    "INT": "integer",
    "INTEGER": "integer",
    "BIGINT": "bigint",
    "FLOAT": "real",
    "DOUBLE": "double precision",
    "DATE": "date",
    "TIMESTAMP": "timestamp with time zone",
    "TIMESTAMP_NTZ": "timestamp without time zone",
    "BINARY": "bytea",
}


def _name(value: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value) or len(value) > 63:
        raise SyncConfigurationError(f"Invalid SQL identifier: {value!r}")
    return value


def _source_name(*parts: str) -> str:
    return ".".join(f"`{_name(part)}`" for part in parts)


def _postgres_type(source_type: str) -> str:
    source_type = source_type.strip().upper()
    match = DECIMAL.fullmatch(source_type)
    if match:
        precision, scale = map(int, match.groups())
        if 1 <= precision <= 38 and 0 <= scale <= precision:
            return f"numeric({precision},{scale})"
    if source_type in TYPE_MAP:
        return TYPE_MAP[source_type]
    if TEXT_TYPE.fullmatch(source_type):
        return "text"
    raise SyncConfigurationError(f"Unsupported Gold column type: {source_type}")


def get_gold_configuration() -> dict:
    required = (
        "DATABRICKS_HOST",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
        "DB_ANALYTICS_HOST",
        "DB_ANALYTICS_PORT",
        "DB_ANALYTICS_USER",
        "DB_ANALYTICS_PASS",
        "DB_ANALYTICS_NAME",
    )
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise SyncConfigurationError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    manifest = json.loads(
        (ROOT / "gold_export_manifest.json").read_text(encoding="utf-8")
    )
    catalog = _name(os.environ.get("DATABRICKS_CATALOG", manifest["catalog"]))
    source_schema = _name(os.environ.get("DATABRICKS_SCHEMA_GOLD", manifest["schema"]))
    if (catalog, source_schema) != (manifest["catalog"], manifest["schema"]):
        raise SyncConfigurationError(
            "Gold source must match the reviewed export manifest"
        )
    tables = manifest["tables"]
    for table, rule in tables.items():
        _name(table)
        if rule["scope"] not in {"ADMIN", "SUPPLIER", "REQUESTER", "PROFESSIONAL"}:
            raise SyncConfigurationError(f"Invalid scope for {table}")
        if rule["scope"] != "ADMIN":
            _name(rule["id_column"])
    try:
        batch_size = int(os.environ.get("GOLD_BATCH_SIZE", "500"))
    except ValueError as exc:
        raise SyncConfigurationError("GOLD_BATCH_SIZE must be an integer") from exc
    if not 1 <= batch_size <= 10000:
        raise SyncConfigurationError("GOLD_BATCH_SIZE must be between 1 and 10000")
    reader_role = os.environ.get("ANALYTICS_READER_ROLE", "").strip()
    if reader_role:
        _name(reader_role)
    return {
        "host": os.environ["DATABRICKS_HOST"].removeprefix("https://").rstrip("/"),
        "http_path": os.environ["DATABRICKS_HTTP_PATH"],
        "token": os.environ["DATABRICKS_TOKEN"],
        "catalog": catalog,
        "source_schema": source_schema,
        "tables": tables,
        "batch_size": batch_size,
        "reader_role": reader_role,
    }


def _describe(cursor, config: dict, table: str, rule: dict) -> list[tuple[str, str]]:
    source = _source_name(config["catalog"], config["source_schema"], table)
    cursor.execute(f"SELECT * FROM {source} LIMIT 0")
    names = [_name(column[0]) for column in cursor.description]
    if len(names) != len(set(names)) or not names:
        raise SyncConfigurationError(f"Invalid Gold schema for {table}")
    if rule.get("id_column") and rule["id_column"] not in names:
        raise SyncConfigurationError(f"{table} does not contain {rule['id_column']}")
    cursor.execute(f"DESCRIBE TABLE {source}")
    described = {row[0]: row[1] for row in cursor.fetchall() if row[0] in names}
    if set(described) != set(names):
        raise SyncConfigurationError(
            f"Cannot determine every Gold column type in {table}"
        )
    return [(name, _postgres_type(described[name])) for name in names]


def _target_columns(cursor, table: str) -> list[tuple[str, str]]:
    cursor.execute(
        """SELECT a.attname, pg_catalog.format_type(a.atttypid, a.atttypmod)
           FROM pg_catalog.pg_attribute a
           JOIN pg_catalog.pg_class c ON c.oid = a.attrelid
           JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'analytics_gold' AND c.relname = %s
             AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum""",
        (table,),
    )
    return [(name, kind.lower().replace(" ", "")) for name, kind in cursor.fetchall()]


def _copy_value(value, kind: str):
    if (
        kind == "timestamp with time zone"
        and isinstance(value, datetime)
        and value.tzinfo is None
    ):
        return value.replace(tzinfo=timezone.utc)
    if (
        kind.startswith("numeric(")
        and value is not None
        and not isinstance(value, Decimal)
    ):
        raise ValueError("Gold decimal values must be exact Decimal instances")
    return value


def _publish_table(
    pg_cursor, dbx_cursor, config: dict, table: str, rule: dict, columns
) -> int:
    target = sql.Identifier("analytics_gold", table)
    staged = sql.Identifier(f"stage_{table}")
    definitions = sql.SQL(", ").join(
        sql.SQL("{} {}").format(sql.Identifier(name), sql.SQL(kind))
        for name, kind in columns
    )
    pg_cursor.execute(
        sql.SQL("CREATE TEMP TABLE {} ({}) ON COMMIT DROP").format(staged, definitions)
    )
    source = _source_name(config["catalog"], config["source_schema"], table)
    dbx_cursor.execute(f"SELECT * FROM {source}")
    names = [column[0] for column in dbx_cursor.description]
    if names != [name for name, _ in columns]:
        raise SyncConfigurationError(f"Gold schema changed during export: {table}")
    insert = (
        sql.SQL("INSERT INTO {} ({}) VALUES %s")
        .format(staged, sql.SQL(", ").join(sql.Identifier(name) for name, _ in columns))
        .as_string(pg_cursor.connection)
    )
    count = 0
    while True:
        rows = dbx_cursor.fetchmany(config["batch_size"])
        if not rows:
            break
        batch = [
            tuple(_copy_value(value, kind) for value, (_, kind) in zip(row, columns))
            for row in rows
        ]
        execute_values(pg_cursor, insert, batch, page_size=config["batch_size"])
        count += len(batch)
    pg_cursor.execute(
        sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(target, definitions)
    )
    expected = [(name, kind.replace(" ", "")) for name, kind in columns]
    if _target_columns(pg_cursor, table) != expected:
        raise SyncConfigurationError(
            f"AnalyticsDB table analytics_gold.{table} differs from Gold; migration required"
        )
    pg_cursor.execute(
        sql.SQL("ALTER TABLE {} ENABLE ROW LEVEL SECURITY").format(target)
    )
    pg_cursor.execute(sql.SQL("ALTER TABLE {} FORCE ROW LEVEL SECURITY").format(target))
    pg_cursor.execute(sql.SQL("DROP POLICY IF EXISTS kpi_read ON {}").format(target))
    if rule["scope"] == "ADMIN":
        allowed = sql.SQL("analytics_gold.can_read('ADMIN', '')")
    else:
        allowed = sql.SQL("analytics_gold.can_read({}, {}::text)").format(
            sql.Literal(rule["scope"]), sql.Identifier(rule["id_column"])
        )
    pg_cursor.execute(
        sql.SQL(
            "CREATE POLICY kpi_read ON {} FOR ALL USING ({}) WITH CHECK ({})"
        ).format(target, allowed, allowed)
    )
    pg_cursor.execute(sql.SQL("TRUNCATE TABLE {}").format(target))
    pg_cursor.execute(sql.SQL("INSERT INTO {} SELECT * FROM {}").format(target, staged))
    if config["reader_role"]:
        pg_cursor.execute(
            sql.SQL("GRANT SELECT ON {} TO {}").format(
                target, sql.Identifier(config["reader_role"])
            )
        )
    return count


def synchronize_gold() -> dict:
    config = get_gold_configuration()
    results = []
    current_table = None
    try:
        with closing(
            dbsql.connect(
                server_hostname=config["host"],
                http_path=config["http_path"],
                access_token=config["token"],
            )
        ) as dbx_conn:
            with closing(dbx_conn.cursor()) as dbx_cursor:
                columns_by_table = {
                    table: _describe(dbx_cursor, config, table, rule)
                    for table, rule in config["tables"].items()
                }
                with (
                    closing(
                        psycopg2.connect(
                            host=os.environ["DB_ANALYTICS_HOST"],
                            port=os.environ["DB_ANALYTICS_PORT"],
                            dbname=os.environ["DB_ANALYTICS_NAME"],
                            user=os.environ["DB_ANALYTICS_USER"],
                            password=os.environ["DB_ANALYTICS_PASS"],
                            sslmode="require",
                            application_name="databricks-sync-gold-export",
                        )
                    ) as pg_conn,
                    pg_conn,
                ):
                    with pg_conn.cursor() as pg_cursor:
                        pg_cursor.execute("SELECT pg_advisory_xact_lock(731827491022)")
                        pg_cursor.execute(
                            "SELECT to_regprocedure('analytics_gold.can_read(text,text)')"
                        )
                        if pg_cursor.fetchone()[0] is None:
                            raise SyncConfigurationError(
                                "Create the AnalyticsDB schema with database-console/db/analytics/schema.sql first"
                            )
                        if config["reader_role"]:
                            pg_cursor.execute(
                                sql.SQL(
                                    "GRANT USAGE ON SCHEMA analytics_gold TO {}"
                                ).format(sql.Identifier(config["reader_role"]))
                            )
                            pg_cursor.execute(
                                sql.SQL(
                                    "GRANT EXECUTE ON FUNCTION analytics_gold.can_read(TEXT, TEXT) TO {}"
                                ).format(sql.Identifier(config["reader_role"]))
                            )
                        for table, rule in config["tables"].items():
                            current_table = table
                            count = _publish_table(
                                pg_cursor,
                                dbx_cursor,
                                config,
                                table,
                                rule,
                                columns_by_table[table],
                            )
                            results.append({"table": table, "rows_synced": count})
    except SyncConfigurationError:
        raise
    except Exception as exc:
        raise SyncExecutionError(
            {
                "status": "failed",
                "tables_total": len(config["tables"]),
                "tables_synced": 0,
                "rows_synced": 0,
                "sources": [],
                "errors": [
                    {
                        "source": "DATABRICKS_GOLD",
                        "dbx_schema": "analytics_gold",
                        "table": current_table,
                        "message": str(exc),
                    }
                ],
            }
        ) from exc
    source = {
        "source": "DATABRICKS_GOLD",
        "dbx_schema": "analytics_gold",
        "tables_total": len(results),
        "tables_synced": len(results),
        "rows_synced": sum(row["rows_synced"] for row in results),
        "errors": [],
    }
    return {
        "status": "completed",
        "tables_total": source["tables_total"],
        "tables_synced": source["tables_synced"],
        "rows_synced": source["rows_synced"],
        "sources": [source],
        "errors": [],
    }


def main() -> int:
    try:
        print(json.dumps(synchronize_gold(), ensure_ascii=False))
        return 0
    except SyncConfigurationError as exc:
        print(str(exc), file=sys.stderr)
    except SyncExecutionError as exc:
        print(json.dumps(exc.summary, ensure_ascii=False), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
