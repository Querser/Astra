"""Additional fictional histories with changing trajectories for forecast demos."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Database, sqlite_url, upgrade_database
from app.models import CrewMember, DataSource, Observation


START = datetime(2026, 10, 12, 8)
SOURCE_VERSION = "forecast-varied-demo-1"
GRADUAL_NAME = "ASTRA — forecast: gradual change"
RECOVERY_NAME = "ASTRA — forecast: recovery"
LEGACY_NAMES = {
    GRADUAL_NAME: "ASTRA — прогноз: постепенное изменение",
    RECOVERY_NAME: "ASTRA — прогноз: восстановление",
}
PROFILES = {
    GRADUAL_NAME: ("moon", "surface", "fictional lunar habitat"),
    RECOVERY_NAME: ("mars", "surface", "fictional Martian habitat"),
}
UNITS = {"heart_rate": "bpm", "spo2": "%", "respiratory_rate": "breaths/min",
         "body_temperature": "°C", "sleep_duration": "h", "sleep_quality": "score",
         "activity": "steps", "exertion_fatigue": "score"}


def values_for(profile: str, day: int) -> dict[str, float]:
    wave = (0, 0.5, -0.5, 0.25, -0.25)[day % 5]
    if profile in {GRADUAL_NAME, LEGACY_NAMES[GRADUAL_NAME]}:
        return {
            "heart_rate": 65 + 0.65 * day + wave,
            "spo2": 99 - 0.045 * day + wave * 0.15,
            "respiratory_rate": 14 + 0.12 * day + wave * 0.2,
            "body_temperature": 36.4 + 0.032 * day + wave * 0.03,
            "sleep_duration": 8.0 - 0.055 * day + wave * 0.06,
            "sleep_quality": 8.5 - 0.075 * day + wave * 0.08,
            "activity": 8200 - 135 * day + wave * 80,
            "exertion_fatigue": 2 + 0.16 * day + wave * 0.1,
        }
    recovery = max(0, day - 10)
    return {
        "heart_rate": 99 - 0.75 * recovery + wave,
        "spo2": 94 + 0.22 * recovery + wave * 0.2,
        "respiratory_rate": 20 - 0.16 * recovery + wave * 0.2,
        "body_temperature": 37.3 - 0.035 * recovery + wave * 0.03,
        "sleep_duration": 5.4 + 0.105 * recovery + wave * 0.06,
        "sleep_quality": 4 + 0.17 * recovery + wave * 0.08,
        "activity": 3900 + 155 * recovery + wave * 80,
        "exertion_fatigue": 7.5 - 0.20 * recovery + wave * 0.1,
    }


def seed_forecast_profiles(session: Session) -> dict[str, int]:
    source = session.scalar(select(DataSource).where(DataSource.version == SOURCE_VERSION))
    if source is None:
        source = DataSource(title="ASTRA varied forecast demonstration", source_type="synthetic",
                            version=SOURCE_VERSION, description="Fictional trajectories for algorithm checks only.")
        session.add(source)
        session.flush()
    result = {}
    for name, (location, phase, habitat) in PROFILES.items():
        crew = session.scalar(select(CrewMember).where(
            CrewMember.display_name.in_((name, LEGACY_NAMES[name])),
            CrewMember.fictional.is_(True),
        ))
        if crew is None:
            crew = CrewMember(display_name=name, fictional=True, mission_location=location,
                              mission_phase=phase, habitat=habitat)
            session.add(crew)
            session.flush()
        existing = {(row.metric, row.observed_at) for row in session.scalars(select(Observation).where(
            Observation.crew_member_id == crew.id, Observation.synthetic.is_(True)))}
        added = 0
        for day in range(28):
            for offset, (metric, value) in enumerate(values_for(name, day).items()):
                observed_at = START + timedelta(days=day, minutes=offset * 5)
                if (metric, observed_at) in existing:
                    continue
                session.add(Observation(crew_member_id=crew.id, source_id=source.id, metric=metric,
                                        value_kind="scalar", scalar_value=round(float(value), 3), unit=UNITS[metric],
                                        observed_at=observed_at, observed_offset_minutes=0, synthetic=True,
                                        quality_flags_json=json.dumps(["synthetic_ui_entry"])))
                added += 1
        result[name] = added
    session.commit()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    database_path = args.database or get_settings().data_dir / "astra.sqlite3"
    url = sqlite_url(database_path)
    upgrade_database(url)
    database = Database(url)
    try:
        with database.session_factory() as session:
            for name, added in seed_forecast_profiles(session).items():
                print(f"{name}: {added} added")
    finally:
        database.dispose()


if __name__ == "__main__":
    main()
