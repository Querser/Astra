"""Explicitly translate known synthetic demo records in an existing ASTRA database.

The default mode is read-only. ``--apply`` first makes a SQLite backup, then
updates exact legacy fixture strings in fictional, seed-owned profiles only.
User-entered records and conversation history are never translated here.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
from uuid import uuid4

from app.demo_seed import LEGACY_NAMES as DEMO_LEGACY_NAMES
from app.forecast_demo_seed import LEGACY_NAMES as FORECAST_LEGACY_NAMES


DEMO_SOURCE_VERSIONS = ("demo-seed-1", "demo-seed-2", "demo-forecast-history-1")
FORECAST_SOURCE_VERSIONS = ("forecast-varied-demo-1",)
LEGACY_HABITATS = {
    "\u0433\u0435\u0440\u043c\u0435\u0442\u0438\u0447\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c \u041c\u041a\u0421": "sealed ISS habitat",
    "\u0432\u044b\u043c\u044b\u0448\u043b\u0435\u043d\u043d\u044b\u0439 \u0433\u0435\u0440\u043c\u0435\u0442\u0438\u0447\u043d\u044b\u0439 \u043b\u0443\u043d\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c": "fictional sealed lunar habitat",
    "\u0432\u044b\u043c\u044b\u0448\u043b\u0435\u043d\u043d\u044b\u0439 \u0433\u0435\u0440\u043c\u0435\u0442\u0438\u0447\u043d\u044b\u0439 \u043c\u0430\u0440\u0441\u0438\u0430\u043d\u0441\u043a\u0438\u0439 \u043c\u043e\u0434\u0443\u043b\u044c": "fictional sealed Martian habitat",
    "\u0443\u0447\u0435\u0431\u043d\u044b\u0439 \u043b\u0443\u043d\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c": "fictional lunar habitat",
    "\u0443\u0447\u0435\u0431\u043d\u044b\u0439 \u043c\u0430\u0440\u0441\u0438\u0430\u043d\u0441\u043a\u0438\u0439 \u043c\u043e\u0434\u0443\u043b\u044c": "fictional Martian habitat",
}
LEGACY_COMPLAINTS = {
    "\u0423\u0447\u0435\u0431\u043d\u0430\u044f \u0436\u0430\u043b\u043e\u0431\u0430: \u043f\u043e\u0441\u043b\u0435 \u043d\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u0441\u0442\u0430\u043b\u043e \u0442\u0440\u0443\u0434\u043d\u0435\u0435 \u0434\u044b\u0448\u0430\u0442\u044c.":
        "Educational complaint: after exertion, it became harder to breathe.",
    "\u0423\u0447\u0435\u0431\u043d\u0430\u044f \u0436\u0430\u043b\u043e\u0431\u0430: \u043e\u0449\u0443\u0449\u0435\u043d\u0438\u0435 \u043e\u0431\u0449\u0435\u0439 \u0441\u043b\u0430\u0431\u043e\u0441\u0442\u0438.":
        "Educational complaint: feeling of general weakness.",
    "\u0423\u0447\u0435\u0431\u043d\u0430\u044f \u0436\u0430\u043b\u043e\u0431\u0430: \u0441\u043e\u043d \u043f\u0440\u0435\u0440\u044b\u0432\u0430\u043b\u0441\u044f, \u0447\u0443\u0432\u0441\u0442\u0432\u0443\u0435\u0442\u0441\u044f \u0443\u0441\u0442\u0430\u043b\u043e\u0441\u0442\u044c.":
        "Educational complaint: sleep was interrupted, feeling of fatigue.",
    "\u0423\u0447\u0435\u0431\u043d\u0430\u044f \u0436\u0430\u043b\u043e\u0431\u0430: \u043d\u0430\u043f\u0430\u0440\u043d\u0438\u043a \u043e\u0442\u043c\u0435\u0447\u0430\u0435\u0442 \u0433\u0440\u043e\u043c\u043a\u0438\u0439 \u0445\u0440\u0430\u043f \u0438 \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0438 \u0434\u044b\u0445\u0430\u043d\u0438\u044f \u0432\u043e \u0441\u043d\u0435; \u0434\u043d\u0451\u043c \u0441\u043e\u043d\u043b\u0438\u0432\u043e\u0441\u0442\u044c.":
        "Educational complaint: partner notes loud snoring and pauses in breathing during sleep; daytime sleepiness.",
}


def plan(connection: sqlite3.Connection) -> list[tuple[str, str, str, str, str]]:
    """Return exact, seed-owned updates as (table, id, field, old, new)."""
    changes: list[tuple[str, str, str, str, str]] = []
    mappings = [(old, new, DEMO_SOURCE_VERSIONS) for new, old in DEMO_LEGACY_NAMES.items()]
    mappings += [(old, new, FORECAST_SOURCE_VERSIONS) for new, old in FORECAST_LEGACY_NAMES.items()]
    for old_name, new_name, versions in mappings:
        rows = connection.execute(
            "SELECT id, habitat FROM crew_members WHERE fictional = 1 AND display_name = ?",
            (old_name,),
        ).fetchall()
        for crew_id, habitat in rows:
            owned = connection.execute(
                "SELECT 1 FROM observations AS o JOIN data_sources AS s ON s.id = o.source_id "
                "WHERE o.crew_member_id = ? AND o.synthetic = 1 AND s.version IN "
                f"({','.join('?' for _ in versions)}) LIMIT 1",
                (crew_id, *versions),
            ).fetchone()
            duplicate = connection.execute(
                "SELECT 1 FROM crew_members WHERE display_name = ? AND id <> ? LIMIT 1",
                (new_name, crew_id),
            ).fetchone()
            if not owned or duplicate:
                continue
            changes.append(("crew_members", crew_id, "display_name", old_name, new_name))
            if habitat in LEGACY_HABITATS:
                changes.append(("crew_members", crew_id, "habitat", habitat, LEGACY_HABITATS[habitat]))
            if versions == DEMO_SOURCE_VERSIONS:
                for report_id, description in connection.execute(
                    "SELECT r.id, r.description FROM symptom_reports AS r "
                    "JOIN data_sources AS s ON s.id = r.source_id "
                    "WHERE r.crew_member_id = ? AND r.synthetic = 1 "
                    "AND s.version IN ('demo-seed-1', 'demo-seed-2')", (crew_id,),
                ):
                    if description in LEGACY_COMPLAINTS:
                        changes.append(("symptom_reports", report_id, "description", description,
                                        LEGACY_COMPLAINTS[description]))
    return changes


def apply(database_path: Path) -> tuple[Path | None, int]:
    """Back up the database, then apply the exact plan in one transaction."""
    path = database_path.resolve(strict=True)
    with sqlite3.connect(path) as connection:
        changes = plan(connection)
        if not changes:
            return None, 0
        backup = path.with_name(f"{path.name}.before-english-demo-{uuid4().hex[:12]}.bak")
        with sqlite3.connect(backup) as target:
            connection.backup(target)
        try:
            connection.execute("BEGIN IMMEDIATE")
            for table, row_id, field, old, new in changes:
                cursor = connection.execute(
                    f"UPDATE {table} SET {field} = ? WHERE id = ? AND {field} = ?",
                    (new, row_id, old),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError(f"Record changed during update: {table}/{row_id}/{field}")
            connection.commit()
        except Exception:
            connection.rollback()
            raise
    return backup, len(changes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="Path to an existing SQLite database")
    parser.add_argument("--apply", action="store_true", help="Back up and apply exact fixture translations")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error("The database file does not exist")
    if args.apply:
        backup, count = apply(args.database)
        print(f"Updated {count} exact fixture fields. Backup: {backup or 'not needed'}")
    else:
        with sqlite3.connect(args.database) as connection:
            changes = plan(connection)
        print(f"Dry run: {len(changes)} exact fixture fields would change. Add --apply to back up and update.")
        for table, row_id, field, old, new in changes:
            print(f"{table}/{row_id}/{field}: {old!r} -> {new!r}")


if __name__ == "__main__":
    main()
