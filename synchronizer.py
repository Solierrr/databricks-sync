import sys

from app.cli import main
from app.config import load_config
from app.errors import SyncConfigurationError, SyncExecutionError
from app.services.sync_service import synchronize as _synchronize


def synchronize() -> dict:
    return _synchronize(load_config())


__all__ = ["SyncConfigurationError", "SyncExecutionError", "main", "synchronize"]

if __name__ == "__main__":
    sys.exit(main())
