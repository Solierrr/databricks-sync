import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.errors import SyncConfigurationError

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

REQUIRED_VARIABLES = (
    "DATABRICKS_HOST",
    "DATABRICKS_HTTP_PATH",
    "DATABRICKS_TOKEN",
    "DATABRICKS_CATALOG",
    "DB_CORE_HOST",
    "DB_CORE_PORT",
    "DB_CORE_USER",
    "DB_CORE_PASS",
    "DB_CORE_NAME",
)

DEFAULT_BATCH_SIZE = 500


@dataclass(frozen=True)
class SourceConfig:
    env_prefix: str
    dbx_schema: str


@dataclass(frozen=True)
class SyncConfig:
    dbx_host: str
    dbx_http_path: str
    dbx_token: str
    dbx_catalog: str
    sources: tuple[SourceConfig, ...]
    batch_size: int = DEFAULT_BATCH_SIZE


def load_env_file() -> None:
    load_dotenv(ENV_PATH)


def load_config(environ: Mapping[str, str] | None = None) -> SyncConfig:
    env = os.environ if environ is None else environ
    missing = [name for name in REQUIRED_VARIABLES if not env.get(name)]
    if missing:
        raise SyncConfigurationError(f"Missing required environment variables: {', '.join(missing)}")

    raw_batch = env.get("SYNC_BATCH_SIZE", str(DEFAULT_BATCH_SIZE))
    try:
        batch_size = int(raw_batch)
    except ValueError:
        batch_size = 0
    if batch_size < 1:
        raise SyncConfigurationError("SYNC_BATCH_SIZE must be a positive integer")

    return SyncConfig(
        dbx_host=env["DATABRICKS_HOST"].replace("https://", ""),
        dbx_http_path=env["DATABRICKS_HTTP_PATH"],
        dbx_token=env["DATABRICKS_TOKEN"],
        dbx_catalog=env["DATABRICKS_CATALOG"],
        sources=(
            SourceConfig("DB_CORE", env.get("DATABRICKS_SCHEMA_CORE", "bronze_core")),
        ),
        batch_size=batch_size,
    )
