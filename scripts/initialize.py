"""Initialize the local ASTRA database and packaged research snapshots."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.db import Database, sqlite_url, upgrade_database  # noqa: E402
from app.research_data import import_packaged_snapshots  # noqa: E402
from app.single_profile import ensure_single_profile  # noqa: E402


def main() -> int:
    settings = get_settings()
    database_url = settings.database_url or sqlite_url(settings.data_dir / "astra.sqlite3")
    upgrade_database(database_url)
    database = Database(database_url)
    try:
        with database.session_factory() as session:
            counts = import_packaged_snapshots(session)
            profile = ensure_single_profile(session)
    finally:
        database.dispose()
    print(f"ASTRA database ready: {database_url}")
    print(f"Packaged research snapshots ready: {counts}")
    print(f"Demo profile ready: {profile['name']} ({profile['observations']} observations added)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
