"""Initialize CAIST SQLite and import the current Stage 4 data products."""

from __future__ import annotations

import json

from src.database.ingest import import_stage4_outputs
from src.database.schema import initialize_database


def main() -> None:
    version = initialize_database()
    result = import_stage4_outputs()
    result["schema_version"] = version
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
