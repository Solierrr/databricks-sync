import uuid

from app.infra.typemap import sql_type_for, to_dbx_value


def test_known_types_map_to_databricks_types():
    assert sql_type_for("integer", None, None) == "INT"
    assert sql_type_for("timestamp with time zone", None, None) == "TIMESTAMP"
    assert sql_type_for("jsonb", None, None) == "STRING"


def test_unknown_type_falls_back_to_string():
    assert sql_type_for("point", None, None) == "STRING"


def test_numeric_uses_precision_and_scale_with_defaults():
    assert sql_type_for("numeric", 12, 2) == "DECIMAL(12,2)"
    assert sql_type_for("numeric", None, None) == "DECIMAL(38,10)"


def test_values_are_converted_for_databricks():
    identifier = uuid.uuid4()
    assert to_dbx_value(identifier) == str(identifier)
    assert to_dbx_value({"a": 1}) == '{"a": 1}'
    assert to_dbx_value([1, 2]) == "[1, 2]"
    assert to_dbx_value(b"\x01\xff") == "01ff"
    assert to_dbx_value("text") == "text"
