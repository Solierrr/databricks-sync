import json
import os
import sys
import uuid
from pathlib import Path

import psycopg2
from databricks import sql as dbsql
from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

PG_TO_SQL_TYPE = {
    "integer": "INT",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "boolean": "BOOLEAN",
    "text": "STRING",
    "character varying": "STRING",
    "character": "STRING",
    "citext": "STRING",
    "uuid": "STRING",
    "json": "STRING",
    "jsonb": "STRING",
    "bytea": "STRING",
    "date": "DATE",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMP",
    "double precision": "DOUBLE",
    "real": "FLOAT",
    "ARRAY": "STRING",
    "USER-DEFINED": "STRING",
}


class SyncConfigurationError(RuntimeError):
    pass


class SyncExecutionError(RuntimeError):
    def __init__(self, summary: dict):
        self.summary = summary
        super().__init__("One or more tables failed to synchronize")


def get_sync_configuration() -> dict:
    required = [
        "DATABRICKS_HOST",
        "DATABRICKS_HTTP_PATH",
        "DATABRICKS_TOKEN",
        "DATABRICKS_CATALOG",
        "DB_CORE_HOST",
        "DB_CORE_PORT",
        "DB_CORE_USER",
        "DB_CORE_PASS",
        "DB_CORE_NAME",
        "DB_AUTH_HOST",
        "DB_AUTH_PORT",
        "DB_AUTH_USER",
        "DB_AUTH_PASS",
        "DB_AUTH_NAME",
    ]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise SyncConfigurationError(f"Missing required environment variables: {', '.join(missing)}")

    return {
        "dbx_host": os.environ["DATABRICKS_HOST"].replace("https://", ""),
        "dbx_http_path": os.environ["DATABRICKS_HTTP_PATH"],
        "dbx_token": os.environ["DATABRICKS_TOKEN"],
        "dbx_catalog": os.environ["DATABRICKS_CATALOG"],
        "sources": [
            {"env_prefix": "DB_CORE", "dbx_schema": os.environ.get("DATABRICKS_SCHEMA_CORE", "bronze_core")},
            {"env_prefix": "DB_AUTH", "dbx_schema": os.environ.get("DATABRICKS_SCHEMA_AUTH", "bronze_auth")},
        ],
    }


def sql_type_for(pg_type: str, precision, scale) -> str:
    if pg_type in ("numeric", "decimal"):
        p = precision or 38
        s = scale or 10
        return f"DECIMAL({p},{s})"
    return PG_TO_SQL_TYPE.get(pg_type, "STRING")


def get_tables(pg_cur) -> list[str]:
    pg_cur.execute(
        """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
    )
    return [r[0] for r in pg_cur.fetchall()]


def get_columns(pg_cur, table: str):
    pg_cur.execute(
        """
        SELECT column_name, data_type, numeric_precision, numeric_scale
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    )
    return pg_cur.fetchall()


def _to_dbx_value(v):
    if isinstance(v, uuid.UUID):
        return str(v)
    if isinstance(v, (dict, list)):
        return json.dumps(v)
    if isinstance(v, (bytes, bytearray)):
        return v.hex()
    return v


def sync_table(pg_cur, dbx_cur, dbx_catalog: str, dbx_schema: str, table: str) -> int:
    columns = get_columns(pg_cur, table)
    col_names = [c[0] for c in columns]
    col_defs = ", ".join(
        f"`{name}` {sql_type_for(pg_type, prec, scale)}"
        for name, pg_type, prec, scale in columns
    )

    full_name = f"`{dbx_catalog}`.`{dbx_schema}`.`{table}`"
    dbx_cur.execute(f"CREATE OR REPLACE TABLE {full_name} ({col_defs})")

    quoted_cols = ", ".join(f'"{c}"' for c in col_names)
    pg_cur.execute(f'SELECT {quoted_cols} FROM public."{table}"')
    rows = pg_cur.fetchall()
    if not rows:
        return 0

    rows = [tuple(_to_dbx_value(v) for v in row) for row in rows]

    placeholders = ", ".join(["?"] * len(col_names))
    col_list = ", ".join(f"`{c}`" for c in col_names)
    insert_sql = f"INSERT INTO {full_name} ({col_list}) VALUES ({placeholders})"

    batch_size = 500
    for i in range(0, len(rows), batch_size):
        batch = rows[i : i + batch_size]
        dbx_cur.executemany(insert_sql, batch)

    return len(rows)


def sync_source(dbx_conn, dbx_catalog: str, env_prefix: str, dbx_schema: str) -> dict:
    pg_conn = psycopg2.connect(
        host=os.environ[f"{env_prefix}_HOST"],
        port=os.environ[f"{env_prefix}_PORT"],
        dbname=os.environ[f"{env_prefix}_NAME"],
        user=os.environ[f"{env_prefix}_USER"],
        password=os.environ[f"{env_prefix}_PASS"],
        sslmode="require",
    )
    pg_cur = pg_conn.cursor()
    dbx_cur = dbx_conn.cursor()
    results = []
    errors = []

    try:
        dbx_cur.execute(f"CREATE SCHEMA IF NOT EXISTS `{dbx_catalog}`.`{dbx_schema}`")
        tables = get_tables(pg_cur)
        print(f"Sincronizando {len(tables)} tabelas de {env_prefix} para {dbx_catalog}.{dbx_schema} ...")

        for table in tables:
            try:
                row_count = sync_table(pg_cur, dbx_cur, dbx_catalog, dbx_schema, table)
                results.append({"table": table, "rows_synced": row_count})
                print(f"  ok  {table}: {row_count} linhas")
            except Exception as exc:
                message = str(exc)
                try:
                    pg_conn.rollback()
                except Exception as rollback_exc:
                    message = f"{message}; Postgres rollback failed: {rollback_exc}"
                errors.append({"source": env_prefix, "dbx_schema": dbx_schema, "table": table, "message": message})
                print(f"  FALHOU {table}: {message}", file=sys.stderr)

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
        pg_cur.close()
        pg_conn.close()


def synchronize() -> dict:
    config = get_sync_configuration()
    source_results = []
    errors = []

    with dbsql.connect(
        server_hostname=config["dbx_host"],
        http_path=config["dbx_http_path"],
        access_token=config["dbx_token"],
    ) as dbx_conn:
        for source in config["sources"]:
            try:
                result = sync_source(
                    dbx_conn,
                    config["dbx_catalog"],
                    source["env_prefix"],
                    source["dbx_schema"],
                )
                source_results.append(result)
                errors.extend(result["errors"])
            except Exception as exc:
                errors.append({
                    "source": source["env_prefix"],
                    "dbx_schema": source["dbx_schema"],
                    "table": None,
                    "message": str(exc),
                })

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


def main():
    try:
        result = synchronize()
    except SyncConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SyncExecutionError as exc:
        print(json.dumps(exc.summary, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    print("Sincronizacao concluida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
