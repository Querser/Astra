"""Import verified, packaged NASA CSV snapshots into a selected ASTRA SQLite DB."""

import argparse
import json
from pathlib import Path

from app.db import Database, sqlite_url, upgrade_database
from app.research_data import import_packaged_snapshots


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="Explicit SQLite path; no implicit user DB changes")
    args = parser.parse_args()
    database_url = sqlite_url(args.database)
    upgrade_database(database_url)
    database = Database(database_url)
    try:
        with database.session_factory() as session:
            print(json.dumps(import_packaged_snapshots(session), ensure_ascii=False))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
