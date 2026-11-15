"""Only exact, seed-owned fictional content may be translated in place."""

import sqlite3

from sqlalchemy import select

from app.db import Database, sqlite_url, upgrade_database
from app.demo_seed import LEGACY_NAMES, RESPIRATORY_NAME, STABLE_NAME, seed_demo_profiles
from app.models import CrewMember, SymptomReport
from translate_demo_records import apply, plan


def test_demo_translation_is_explicit_backed_up_and_idempotent(tmp_path):
    path = tmp_path / "existing.sqlite3"
    url = sqlite_url(path)
    upgrade_database(url)
    database = Database(url)
    with database.session_factory() as session:
        seed_demo_profiles(session)
        stable = session.scalar(select(CrewMember).where(CrewMember.display_name == STABLE_NAME))
        stable.display_name = LEGACY_NAMES[STABLE_NAME]
        stable.habitat = "герметичный модуль МКС"
        respiratory = session.scalar(select(CrewMember).where(CrewMember.display_name == RESPIRATORY_NAME))
        respiratory.display_name = LEGACY_NAMES[RESPIRATORY_NAME]
        respiratory.habitat = "вымышленный герметичный лунный модуль"
        report = session.scalar(select(SymptomReport).where(SymptomReport.crew_member_id == respiratory.id))
        report.description = "Учебная жалоба: после нагрузки стало труднее дышать."
        real = CrewMember(display_name="Private Russian profile", fictional=False)
        session.add(real)
        session.commit()
        stable_id, respiratory_id, report_id, real_id = stable.id, respiratory.id, report.id, real.id
    database.dispose()

    with sqlite3.connect(path) as connection:
        changes = plan(connection)
        assert len(changes) == 5
        assert all(row_id != real_id for _, row_id, *_ in changes)
        assert connection.execute("SELECT display_name FROM crew_members WHERE id=?", (stable_id,)).fetchone()[0] == LEGACY_NAMES[STABLE_NAME]

    backup, count = apply(path)
    assert count == 5 and backup and backup.is_file()
    with sqlite3.connect(backup) as old, sqlite3.connect(path) as new:
        assert old.execute("SELECT display_name FROM crew_members WHERE id=?", (stable_id,)).fetchone()[0] == LEGACY_NAMES[STABLE_NAME]
        assert new.execute("SELECT display_name, habitat FROM crew_members WHERE id=?", (stable_id,)).fetchone() == (STABLE_NAME, "sealed ISS habitat")
        assert new.execute("SELECT display_name FROM crew_members WHERE id=?", (respiratory_id,)).fetchone()[0] == RESPIRATORY_NAME
        assert new.execute("SELECT description FROM symptom_reports WHERE id=?", (report_id,)).fetchone()[0].startswith("Educational complaint:")
        assert new.execute("SELECT display_name FROM crew_members WHERE id=?", (real_id,)).fetchone()[0] == "Private Russian profile"
    assert apply(path) == (None, 0)
