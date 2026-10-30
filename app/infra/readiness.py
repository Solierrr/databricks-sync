import json
import os
import urllib.request
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor

from app.config import load_config

TIMEOUT_SECONDS = 2


def ping_postgres(env_prefix: str, environ: Mapping[str, str]) -> None:
    import psycopg2

    conn = psycopg2.connect(
        host=environ[f"{env_prefix}_HOST"],
        port=environ[f"{env_prefix}_PORT"],
        dbname=environ[f"{env_prefix}_NAME"],
        user=environ[f"{env_prefix}_USER"],
        password=environ[f"{env_prefix}_PASS"],
        sslmode="require",
        connect_timeout=TIMEOUT_SECONDS,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
    finally:
        conn.close()


def ping_databricks(host: str, http_path: str, token: str) -> None:
    warehouse_id = http_path.rstrip("/").rsplit("/", 1)[-1]
    request = urllib.request.Request(
        f"https://{host}/api/2.0/sql/warehouses/{warehouse_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        json.load(response)


def check_dependencies(environ: Mapping[str, str] | None = None) -> bool:
    env = os.environ if environ is None else environ
    try:
        config = load_config(env)
    except Exception:
        return False
    checks = [lambda: ping_databricks(config.dbx_host, config.dbx_http_path, config.dbx_token)]
    prefixes = [source.env_prefix for source in config.sources]
    if env.get("DB_ANALYTICS_HOST"):
        prefixes.append("DB_ANALYTICS")
    checks += [lambda prefix=prefix: ping_postgres(prefix, env) for prefix in prefixes]
    with ThreadPoolExecutor(max_workers=len(checks)) as pool:
        futures = [pool.submit(check) for check in checks]
        try:
            for future in futures:
                future.result()
        except Exception:
            return False
    return True
