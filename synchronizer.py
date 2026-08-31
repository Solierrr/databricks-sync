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

DBX_HOST = os.environ["DATABRICKS_HOST"].replace("https://", "")
DBX_HTTP_PATH = os.environ["DATABRICKS_HTTP_PATH"]
DBX_TOKEN = os.environ["DATABRICKS_TOKEN"]
DBX_CATALOG = os.environ["DATABRICKS_CATALOG"]

# Cada banco Postgres sincronizado tem seu proprio schema de destino no
# Databricks (bronze layer), para nao misturar tabelas do dominio core com
# as do dominio auth.
SOURCES = [
    {"env_prefix": "DB_CORE", "dbx_schema": os.environ.get("DATABRICKS_SCHEMA_CORE", "bronze_core")},
    {"env_prefix": "DB_AUTH", "dbx_schema": os.environ.get("DATABRICKS_SCHEMA_AUTH", "bronze_auth")},
]

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


def sync_table(pg_cur, dbx_cur, dbx_schema: str, table: str) -> int:
    columns = get_columns(pg_cur, table)
    col_names = [c[0] for c in columns]
    col_defs = ", ".join(
        f"`{name}` {sql_type_for(pg_type, prec, scale)}"
        for name, pg_type, prec, scale in columns
    )

    full_name = f"`{DBX_CATALOG}`.`{dbx_schema}`.`{table}`"
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


def sync_source(dbx_conn, env_prefix: str, dbx_schema: str) -> None:
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

    dbx_cur.execute(f"CREATE SCHEMA IF NOT EXISTS `{DBX_CATALOG}`.`{dbx_schema}`")

    tables = get_tables(pg_cur)
    print(f"Sincronizando {len(tables)} tabelas de {env_prefix} para {DBX_CATALOG}.{dbx_schema} ...")
    for table in tables:
        try:
            n = sync_table(pg_cur, dbx_cur, dbx_schema, table)
            print(f"  ok  {table}: {n} linhas")
        except Exception as exc:
            print(f"  FALHOU {table}: {exc}", file=sys.stderr)

    dbx_cur.close()
    pg_cur.close()
    pg_conn.close()


def main():
    with dbsql.connect(
        server_hostname=DBX_HOST,
        http_path=DBX_HTTP_PATH,
        access_token=DBX_TOKEN,
    ) as dbx_conn:
        for source in SOURCES:
            sync_source(dbx_conn, source["env_prefix"], source["dbx_schema"])

    print("Sincronizacao concluida.")


if __name__ == "__main__":
    main()
