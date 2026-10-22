import json
import logging
import sys

from app.config import load_config, load_env_file
from app.errors import SyncConfigurationError, SyncExecutionError
from app.services.sync_service import synchronize


def main() -> int:
    load_env_file()
    logging.basicConfig(level=logging.INFO)
    try:
        result = synchronize(load_config())
    except SyncConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except SyncExecutionError as exc:
        print(json.dumps(exc.summary, ensure_ascii=False), file=sys.stderr)
        return 1
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    print("Sincronizacao concluida.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
