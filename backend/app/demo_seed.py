"""Reproducible, explicitly synthetic crew histories for local ASTRA demos."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Database, sqlite_url, upgrade_database
from app.models import CrewMember, DataSource, EnvironmentalMeasurement, Observation, SymptomReport


FIRST_DAY = datetime(2026, 11, 1, 8, 0, 0)  # UTC, deliberately fixed for reproducibility
RECOVERY_NAME = "ASTRA — single drop in SpO₂"
STABLE_NAME = "ASTRA — stable demo profile"
RESPIRATORY_NAME = "ASTRA — respiratory changes"
SLEEP_NAME = "ASTRA — sleep and exertion changes"
PRESSURE_NAME = "ASTRA — elevated blood pressure"
LEGACY_NAMES = {
    STABLE_NAME: "ASTRA — \u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u044b\u0439 \u0443\u0447\u0435\u0431\u043d\u044b\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c",
    RESPIRATORY_NAME: "ASTRA — \u0434\u044b\u0445\u0430\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f",
    SLEEP_NAME: "ASTRA — \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u044f \u0441\u043d\u0430 \u0438 \u043d\u0430\u0433\u0440\u0443\u0437\u043a\u0438",
    PRESSURE_NAME: "ASTRA — \u043f\u043e\u0432\u044b\u0448\u0435\u043d\u043d\u043e\u0435 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435",
    RECOVERY_NAME: "ASTRA — \u0435\u0434\u0438\u043d\u0438\u0447\u043d\u043e\u0435 \u0441\u043d\u0438\u0436\u0435\u043d\u0438\u0435 SpO₂",
}
METRICS = (
    ("heart_rate", "bpm"),
    ("spo2", "%"),
    ("respiratory_rate", "breaths/min"),
    ("body_temperature", "°C"),
    ("sleep_duration", "h"),
    ("sleep_quality", "score"),
    ("activity", "steps"),
    ("exertion_fatigue", "score"),
)
PROFILES: tuple[tuple[str, dict[str, tuple[float, ...]], tuple[str, ...]], ...] = (
    (
        STABLE_NAME,
        {
            "heart_rate": (70, 72, 69, 71, 73, 70, 72),
            "spo2": (98, 98, 97, 99, 98, 97, 98),
            "respiratory_rate": (15, 16, 15, 14, 16, 15, 16),
            "body_temperature": (36.6, 36.5, 36.7, 36.6, 36.5, 36.7, 36.6),
            "sleep_duration": (7.6, 7.8, 7.4, 7.7, 7.5, 7.9, 7.6),
            "sleep_quality": (7, 8, 7, 7, 8, 7, 8),
            "activity": (6000, 6200, 5900, 6500, 6100, 6300, 6200),
            "exertion_fatigue": (3, 2, 3, 3, 2, 3, 2),
        },
        (),
    ),
    (
        RESPIRATORY_NAME,
        {
            "heart_rate": (88, 90, 93, 96, 101, 106, 112),
            "spo2": (97, 96, 96, 95, 94, 93, 91),
            "respiratory_rate": (17, 18, 19, 20, 21, 22, 24),
            "body_temperature": (36.6, 36.7, 36.6, 36.8, 36.9, 36.8, 36.9),
            "sleep_duration": (7.4, 7.2, 7.0, 7.1, 7.0, 7.1, 7.0),
            "sleep_quality": (7, 7, 6, 6, 5, 4, 4),
            "activity": (6000, 5700, 5200, 4800, 4300, 3900, 3400),
            "exertion_fatigue": (3, 4, 4, 5, 6, 7, 8),
        },
        (
            "Educational complaint: after exertion, it became harder to breathe.",
            "Educational complaint: feeling of general weakness.",
        ),
    ),
    (
        SLEEP_NAME,
        {
            "heart_rate": (72, 74, 76, 77, 79, 82, 86),
            "spo2": (98, 97, 98, 97, 98, 97, 98),
            "respiratory_rate": (15, 15, 16, 15, 16, 17, 16),
            "body_temperature": (36.6, 36.6, 36.5, 36.7, 36.6, 36.7, 36.6),
            "sleep_duration": (7.8, 7.4, 7.0, 6.5, 6.0, 5.5, 5.0),
            "sleep_quality": (8, 7, 7, 6, 5, 4, 3),
            "activity": (6500, 6300, 6000, 5500, 5000, 4200, 3500),
            "exertion_fatigue": (2, 3, 3, 4, 5, 7, 8),
        },
        ("Educational complaint: sleep was interrupted, feeling of fatigue.",),
    ),
    (
        PRESSURE_NAME,
        {
            "heart_rate": (74, 75, 76, 78, 77, 79, 80),
            "spo2": (98, 98, 97, 98, 97, 98, 98),
            "respiratory_rate": (15, 16, 15, 16, 15, 16, 15),
            "body_temperature": (36.6, 36.5, 36.6, 36.7, 36.6, 36.5, 36.6),
            "sleep_duration": (7.5, 7.4, 7.6, 7.3, 7.5, 7.2, 7.4),
            "sleep_quality": (7, 7, 8, 7, 7, 7, 7),
            "activity": (5900, 6100, 6000, 5800, 6200, 6000, 5900),
            "exertion_fatigue": (3, 3, 3, 4, 3, 3, 4),
        },
        ("Educational complaint: partner notes loud snoring and pauses in breathing during sleep; daytime sleepiness.",),
    ),
    (
        RECOVERY_NAME,
        {
            "heart_rate": (70, 72, 71, 69, 72, 70, 71),
            "spo2": (98, 98, 97, 99, 98, 97, 98),
            "respiratory_rate": (15, 15, 16, 15, 14, 15, 15),
            "body_temperature": (36.6, 36.7, 36.6, 36.5, 36.6, 36.7, 36.6),
            "sleep_duration": (7.5, 7.6, 7.4, 7.7, 7.5, 7.8, 7.6),
            "sleep_quality": (7, 7, 8, 7, 8, 7, 8),
            "activity": (6100, 6000, 6200, 5900, 6300, 6200, 6100),
            "exertion_fatigue": (3, 3, 2, 3, 2, 3, 2),
        },
        (),
    ),
)

MISSION_ASSIGNMENTS = {
    STABLE_NAME: ("iss", "orbit", "sealed ISS habitat", 22.0, 45.0),
    RESPIRATORY_NAME: ("moon", "surface", "fictional sealed lunar habitat", 21.0, 40.0),
    SLEEP_NAME: ("mars", "surface", "fictional sealed Martian habitat", 20.0, 38.0),
    PRESSURE_NAME: ("iss", "orbit", "sealed ISS habitat", 22.0, 44.0),
    RECOVERY_NAME: ("iss", "orbit", "sealed module of the ISS", 22.0, 45.0),
}
APNEA_COMPLAINT = "Complaint: partner notes loud snoring and pauses in breathing during sleep; daytime sleepiness."

BLOOD_PRESSURE_SERIES: dict[str, tuple[tuple[tuple[float, float], tuple[float, float]], ...]] = {
    PRESSURE_NAME: (
        ((143, 92), (145, 93)), ((146, 94), (148, 95)),
        ((144, 92), (147, 94)), ((149, 95), (150, 96)),
        ((146, 94), (148, 95)), ((151, 97), (149, 95)),
        ((152, 98), (150, 96)),
    ),
}


def seed_demo_profiles(session: Session) -> list[dict[str, str | int]]:
    """Seed an empty database; refuse to overwrite any existing user records."""

    if session.scalar(select(func.count()).select_from(CrewMember)) or session.scalar(
        select(func.count()).select_from(DataSource)
    ):
        raise ValueError("Database is not empty. This seed function never clears existing data.")
    source = DataSource(
        title="ASTRA synthetic extended demonstration",
        source_type="synthetic",
        version="demo-seed-2",
        description="Entirely invented values for software testing; not medical evidence.",
    )
    session.add(source)
    session.flush()
    result: list[dict[str, str | int]] = []
    for name, values, symptoms in PROFILES:
        crew = CrewMember(display_name=name, fictional=True)
        session.add(crew)
        session.flush()
        count = 0
        for day in range(7):
            for metric_index, (metric, unit) in enumerate(METRICS):
                observed_at = FIRST_DAY + timedelta(days=day, minutes=metric_index * 5)
                session.add(Observation(
                    crew_member_id=crew.id,
                    source_id=source.id,
                    metric=metric,
                    value_kind="scalar",
                    scalar_value=float(values[metric][day]),
                    unit=unit,
                    observed_at=observed_at,
                    observed_offset_minutes=0,
                    synthetic=True,
                    quality_flags_json=json.dumps(["synthetic_ui_entry"]),
                ))
                count += 1
            pressure_readings = BLOOD_PRESSURE_SERIES[name][day] if name in BLOOD_PRESSURE_SERIES else ()
            for bp_index, (systolic, diastolic) in enumerate(pressure_readings):
                session.add(Observation(
                    crew_member_id=crew.id,
                    source_id=source.id,
                    metric="blood_pressure",
                    value_kind="blood_pressure",
                    systolic=float(systolic),
                    diastolic=float(diastolic),
                    unit="mmHg",
                    observed_at=FIRST_DAY + timedelta(days=day, hours=1, minutes=bp_index * 10),
                    observed_offset_minutes=0,
                    synthetic=True,
                    quality_flags_json=json.dumps(["synthetic_ui_entry"]),
                ))
                count += 1
        for index, description in enumerate(symptoms):
            session.add(SymptomReport(
                crew_member_id=crew.id,
                source_id=source.id,
                description=description,
                observed_at=FIRST_DAY + timedelta(days=5 + index, hours=2),
                observed_offset_minutes=0,
                synthetic=True,
            ))
        result.append({"crew_id": crew.id, "name": name, "observations": count, "symptoms": len(symptoms)})
    enrich_demo_profiles(session)
    extend_demo_histories(session)
    session.commit()
    for item in result:
        item["observations"] = session.scalar(select(func.count()).select_from(Observation).where(Observation.crew_member_id == item["crew_id"])) or 0
    return result


def extend_demo_histories(session: Session) -> dict[str, int]:
    """Idempotently add twenty earlier days to known fictional profiles only."""
    source = session.scalar(select(DataSource).where(DataSource.version == "demo-forecast-history-1"))
    if source is None:
        source = DataSource(title="ASTRA synthetic forecast history", source_type="synthetic",
                            version="demo-forecast-history-1",
                            description="Invented values to exercise chronological forecast evaluation.")
        session.add(source)
        session.flush()
    profiles = {name: values for name, values, _ in PROFILES}
    added: dict[str, int] = {}
    for name, values in profiles.items():
        crew = session.scalar(select(CrewMember).where(
            CrewMember.display_name.in_((name, LEGACY_NAMES[name])),
            CrewMember.fictional.is_(True),
        ).limit(1))
        if crew is None:
            if name != RECOVERY_NAME:
                continue
            crew = CrewMember(display_name=name, fictional=True)
            session.add(crew)
            session.flush()
        existing = {(row.metric, row.observed_at) for row in session.scalars(
            select(Observation).where(Observation.crew_member_id == crew.id, Observation.synthetic.is_(True))
        )}
        count = 0
        for day in range(-20, 7 if name == RECOVERY_NAME else 0):
            for metric_index, (metric, unit) in enumerate(METRICS):
                observed_at = FIRST_DAY + timedelta(days=day, minutes=metric_index * 5)
                if (metric, observed_at) in existing:
                    continue
                if day >= 0:
                    value = float(values[metric][day])
                elif name == RECOVERY_NAME and metric == "spo2":
                    value = 91.0 if day == -1 else float((98, 97, 99, 98, 97)[(day + 20) % 5])
                else:
                    base = float(values[metric][0])
                    change = (day + 20) % 3 - 1
                    amplitude = 0.1 if metric == "body_temperature" else 0.2 if metric == "sleep_duration" else 100 if metric == "activity" else 1
                    value = max(0.0, base + change * amplitude)
                session.add(Observation(
                    crew_member_id=crew.id, source_id=source.id, metric=metric,
                    value_kind="scalar", scalar_value=value, unit=unit,
                    observed_at=observed_at, observed_offset_minutes=0, synthetic=True,
                    quality_flags_json=json.dumps(["synthetic_ui_entry"]),
                ))
                count += 1
            if name == PRESSURE_NAME and day < 0:
                for bp_index, (sys, dia) in enumerate(((140, 90), (142, 91))):
                    observed_at = FIRST_DAY + timedelta(days=day, hours=1, minutes=bp_index * 10)
                    if ("blood_pressure", observed_at) not in existing:
                        session.add(Observation(
                            crew_member_id=crew.id, source_id=source.id, metric="blood_pressure",
                            value_kind="blood_pressure", systolic=float(sys), diastolic=float(dia),
                            unit="mmHg", observed_at=observed_at, observed_offset_minutes=0,
                            synthetic=True, quality_flags_json=json.dumps(["synthetic_ui_entry"]),
                        ))
                        count += 1
        added[name] = count
    session.flush()
    enrich_demo_profiles(session)
    return added


def enrich_demo_profiles(session: Session) -> None:
    """Add missing mission context to known fictional profiles without replacing other records."""
    source = session.scalar(select(DataSource).where(DataSource.source_type == "synthetic").limit(1))
    if source is None:
        raise ValueError("No synthetic source exists for demo enrichment")
    for crew in session.scalars(select(CrewMember).where(CrewMember.fictional.is_(True))):
        canonical = next((name for name, legacy in LEGACY_NAMES.items()
                          if crew.display_name in {name, legacy}), None)
        assignment = MISSION_ASSIGNMENTS.get(canonical)
        if assignment is None:
            continue
        location, phase, habitat, temperature, humidity = assignment
        if crew.mission_location is None:
            crew.mission_location, crew.mission_phase, crew.habitat = location, phase, habitat
        existing = {item.metric for item in session.scalars(
            select(EnvironmentalMeasurement).where(EnvironmentalMeasurement.crew_member_id == crew.id)
        )}
        for metric, value, unit in (("air_temperature", temperature, "°C"), ("humidity", humidity, "%")):
            if metric not in existing:
                session.add(EnvironmentalMeasurement(
                    crew_member_id=crew.id, source_id=source.id, metric=metric, value=value,
                    unit=unit, observed_at=FIRST_DAY + timedelta(days=6, hours=2), synthetic=True,
                ))
        if crew.display_name in {PRESSURE_NAME, LEGACY_NAMES[PRESSURE_NAME]} and not session.scalar(
            select(SymptomReport.id).where(
                SymptomReport.crew_member_id == crew.id,
                or_(SymptomReport.description.contains("snoring"), SymptomReport.description.contains("snoring")),
            ).limit(1)
        ):
            session.add(SymptomReport(
                crew_member_id=crew.id, source_id=source.id, description=APNEA_COMPLAINT,
                observed_at=FIRST_DAY + timedelta(days=6, hours=3), observed_offset_minutes=0, synthetic=True,
            ))
    session.flush()


def main() -> None:
    parser = argparse.ArgumentParser(description="Add five synthetic ASTRA profiles to an empty local database.")
    parser.add_argument("--database", type=Path, help="Explicit SQLite path; defaults to ASTRA_DATA_DIR/astra.sqlite3")
    parser.add_argument("--extend-existing", action="store_true", help="Idempotently extend only known fictional profiles; preserve all other records")
    args = parser.parse_args()
    path = args.database or get_settings().data_dir / "astra.sqlite3"
    url = sqlite_url(path)
    upgrade_database(url)
    database = Database(url)
    try:
        with database.session_factory() as session:
            if args.extend_existing:
                result = extend_demo_histories(session)
                session.commit()
            else:
                result = seed_demo_profiles(session)
        print(json.dumps(result, ensure_ascii=True, indent=2))
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
