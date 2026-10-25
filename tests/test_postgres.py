from app.infra.postgres import PostgresSource


class RecordingCursor:
    def __init__(self, result):
        self.result = result
        self.executed = []
        self.itersize = None

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.result

    def fetchmany(self, size):
        rows, self.result = self.result[:size], self.result[size:]
        return rows

    def close(self):
        pass


class RecordingConnection:
    def __init__(self, result=()):
        self.cursor_instance = RecordingCursor(list(result))

    def cursor(self, name=None):
        return self.cursor_instance


def test_tables_lists_only_views_of_the_export_schema():
    connection = RecordingConnection([("a",), ("b",)])

    assert PostgresSource(connection).tables() == ["a", "b"]

    sql, params = connection.cursor_instance.executed[0]
    assert "table_schema = %s" in sql
    assert "table_type = 'VIEW'" in sql
    assert params == ("export",)


def test_columns_reads_the_export_schema():
    connection = RecordingConnection([("id", "integer", None, None)])

    assert PostgresSource(connection).columns("offer") == [("id", "integer", None, None)]

    sql, params = connection.cursor_instance.executed[0]
    assert "table_schema = %s AND table_name = %s" in sql
    assert params == ("export", "offer")


def test_rows_select_from_the_export_view():
    connection = RecordingConnection([(1, "a")])

    batches = list(PostgresSource(connection).rows("offer", ["id", "name"], 10))

    assert batches == [[(1, "a")]]
    assert connection.cursor_instance.executed[0][0] == 'SELECT "id", "name" FROM "export"."offer"'
