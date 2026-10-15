from app.config import SyncConfig


def connect(config: SyncConfig):
    from databricks import sql as dbsql

    return dbsql.connect(
        server_hostname=config.dbx_host,
        http_path=config.dbx_http_path,
        access_token=config.dbx_token,
    )
