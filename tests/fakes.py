class FakeDbxCursor:
    def __init__(self):
        self.statements: list[str] = []
        self.batches: list[list[tuple]] = []
        self.fail_on: str | None = None

    def execute(self, sql, params=None):
        if self.fail_on and self.fail_on in sql:
            raise RuntimeError("databricks failure")
        self.statements.append(sql)

    def executemany(self, sql, rows):
        self.statements.append(sql)
        self.batches.append(list(rows))

    def close(self):
        pass


class FakeDbxConnection:
    def __init__(self, cursor: FakeDbxCursor):
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSource:
    def __init__(self, tables: dict[str, list[tuple]], columns: dict[str, list[tuple]] | None = None):
        self._tables = tables
        self._columns = columns or {}
        self.rolled_back = 0
        self.closed = False

    def tables(self):
        return list(self._tables)

    def columns(self, table):
        return self._columns.get(table, [("id", "integer", None, None), ("name", "text", None, None)])

    def rows(self, table, columns, size):
        rows = self._tables[table]
        if rows == "boom":
            raise RuntimeError("postgres failure")
        for start in range(0, len(rows), size):
            yield rows[start : start + size]

    def rollback(self):
        self.rolled_back += 1

    def close(self):
        self.closed = True
