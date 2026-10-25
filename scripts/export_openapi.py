import os
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["DOCS_ENABLED"] = "true"

from app.main import create_app  # noqa: E402
from app.openapi import build_openapi  # noqa: E402


class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def main() -> None:
    contract = yaml.dump(
        build_openapi(create_app(), include_internal=True),
        Dumper=_Dumper,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
    lines = contract.splitlines()
    marked = False
    for index, line in enumerate(lines):
        if not marked and line.startswith("  version: "):
            lines[index] = f"{line} # x-release-please-version"
            marked = True
    (ROOT / "openapi.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
