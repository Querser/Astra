"""Maintain the one English synthetic profile used by the local demonstration."""

import json
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import (
    Alert, AnalysisResult, AuditEvent, ChatMemory, ChatMessage, CrewMember,
    DataSource, EmergencyHandoff, EnvironmentalMeasurement, Forecast,
    Observation, PsychologicalAssessment, ScenarioRun, SymptomReport,
    WhatIfScenario,
)

PROFILE_NAME = "ASTRA Demo Astronaut"
SOURCE_VERSION = "single-english-profile-1"
METRICS = (("heart_rate", "bpm"), ("spo2", "%"), ("respiratory_rate", "breaths/min"),
           ("body_temperature", "°C"), ("sleep_duration", "h"), ("sleep_quality", "score"),
           ("activity", "steps"), ("exertion_fatigue", "score"))


def _purge(session: Session) -> int:
    ids = list(session.scalars(select(CrewMember.id).where(CrewMember.fictional.is_(True))))
    if not ids:
        return 0
    for model in (ChatMessage, Alert, Forecast, PsychologicalAssessment, EnvironmentalMeasurement,
                  WhatIfScenario, EmergencyHandoff, ScenarioRun, ChatMemory, AnalysisResult,
                  AuditEvent):
        column = getattr(model, "crew_member_id", None)
        if column is not None:
            session.execute(delete(model).where(column.in_(ids)))
    session.execute(delete(Observation).where(Observation.crew_member_id.in_(ids)))
    session.execute(delete(SymptomReport).where(SymptomReport.crew_member_id.in_(ids)))
    session.execute(delete(CrewMember).where(CrewMember.id.in_(ids)))
    session.flush()
    return len(ids)


def ensure_single_profile(session: Session) -> dict[str, int | str]:
    removed = _purge(session)
    profile = session.scalar(select(CrewMember).where(CrewMember.display_name == PROFILE_NAME, CrewMember.fictional.is_(True)))
    if profile is None:
        profile = CrewMember(display_name=PROFILE_NAME, fictional=True, mission_location="iss",
                             mission_phase="orbital segment", habitat="ISS")
        session.add(profile)
        session.flush()
    source = session.scalar(select(DataSource).where(DataSource.version == SOURCE_VERSION))
    if source is None:
        source = DataSource(title="ASTRA synthetic demonstration", source_type="synthetic",
                            version=SOURCE_VERSION, description="Synthetic demo data only.")
        session.add(source)
        session.flush()
    existing = session.scalar(select(Observation.id).where(Observation.crew_member_id == profile.id))
    added = 0
    if existing is None:
        start = datetime(2026, 10, 12, 8)
        for day in range(28):
            values = (70 + day % 4, 97 + (day % 3), 15 + (day % 2), 36.5 + (day % 3) * .1,
                      7.0 + (day % 4) * .2, 7 + (day % 2), 5600 + day * 90, 3 + (day % 3))
            for index, ((metric, unit), value) in enumerate(zip(METRICS, values)):
                session.add(Observation(crew_member_id=profile.id, source_id=source.id, metric=metric,
                    value_kind="scalar", scalar_value=float(value), unit=unit,
                    observed_at=start + timedelta(days=day, minutes=index * 5), observed_offset_minutes=0,
                    synthetic=True, quality_flags_json=json.dumps(["synthetic_demo_data"])))
                added += 1
        session.add_all([
            EnvironmentalMeasurement(source_id=source.id, crew_member_id=profile.id, metric="radiation", value=6.5, unit="µGy/hour", observed_at=start, synthetic=True),
            EnvironmentalMeasurement(source_id=source.id, crew_member_id=profile.id, metric="co2", value=0.08, unit="%", observed_at=start, synthetic=True),
        ])
        session.commit()
    return {"name": PROFILE_NAME, "removed_profiles": removed, "observations": added}
