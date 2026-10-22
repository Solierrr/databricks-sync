import json
import uuid

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


def to_dbx_value(value):
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value)
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return value
