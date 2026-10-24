import os
import uuid
from collections.abc import Iterator, Mapping

EXPORT_SCHEMA = "export"


class PostgresSource:
    def __init__(self, connection):
        self._conn = connection

    @classmethod
    def connect(cls, env_prefix: str, environ: Mapping[str, str] | None = None) -> "PostgresSource":
        import psycopg2

        env = os.environ if environ is None else environ
        return cls(
            psycopg2.connect(
                host=env[f"{env_prefix}_HOST"],
                port=env[f"{env_prefix}_PORT"],
                dbname=env[f"{env_prefix}_NAME"],
                user=env[f"{env_prefix}_USER"],
                password=env[f"{env_prefix}_PASS"],
                sslmode="require",
            )
        )

    def tables(self) -> list[str]:
        cur = self._conn.cursor()
        try:
            cur.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = %s AND table_type = 'VIEW'
                ORDER BY table_name
                """,
                (EXPORT_SCHEMA,),
            )
            return [row[0] for row in cur.fetchall()]
        finally:
            cur.close()

    def columns(self, table: str) -> list[tuple]:
        cur = self._conn.cursor()
        try:
            cur.execute(
                """
                SELECT column_name, data_type, numeric_precision, numeric_scale
                FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                ORDER BY ordinal_position
                """,
                (EXPORT_SCHEMA, table),
            )
            return cur.fetchall()
        finally:
            cur.close()

    def rows(self, table: str, columns: list[str], size: int) -> Iterator[list[tuple]]:
        quoted = ", ".join(f'"{name}"' for name in columns)
        cur = self._conn.cursor(name=f"sync_{uuid.uuid4().hex}")
        cur.itersize = size
        try:
            cur.execute(f'SELECT {quoted} FROM "{EXPORT_SCHEMA}"."{table}"')
            while True:
                batch = cur.fetchmany(size)
                if not batch:
                    break
                yield batch
        finally:
            cur.close()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()
