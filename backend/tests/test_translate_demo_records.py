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
        stable.habitat = "\u0433\u0435\u0440\u043c\u0435\u0442\u0438\u0447\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c \u041c\u041a\u0421"
        respiratory = session.scalar(select(CrewMember).where(CrewMember.display_name == RESPIRATORY_NAME))
        respiratory.display_name = LEGACY_NAMES[RESPIRATORY_NAME]
        respiratory.habitat = "\u0432\u044b\u043c\u044b\u0448\u043b\u0435\u043d\u043d\u044b\u0439 \u0433\u0435\u0440\u043c\u0435\u0442\u0438\u0447\u043d\u044b\u0439 \u043b\u0443\u043d\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c"
        report = session.scalar(select(SymptomReport).where(SymptomReport.crew_member_id == respiratory.id))
        report.description = "\u0423\u0447\u0435\u0431\u043d\u0430\u044f \u0436\u0430\u043b\u043e\u0431\u0430: \u043f\u043e\u0441\u043b\u0435 \u043d\u0430\u0433\u0440\u0443\u0437\u043a\u0438 \u0441\u0442\u0430\u043b\u043e \u0442\u0440\u0443\u0434\u043d\u0435\u0435 \u0434\u044b\u0448\u0430\u0442\u044c."
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
