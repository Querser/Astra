"""SQLAlchemy persistence models. They contain no clinical interpretation."""

from datetime import datetime
import json
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id() -> str:
    return str(uuid4())


def utc_now_naive() -> datetime:
    """Store UTC consistently; API schemas restore explicit UTC on output."""

    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class CrewMember(Base):
    __tablename__ = "crew_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    display_name: Mapped[str] = mapped_column(String(80), nullable=False)
    fictional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    mission_location: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mission_phase: Mapped[str | None] = mapped_column(String(40), nullable=True)
    habitat: Mapped[str | None] = mapped_column(String(80), nullable=True)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=utc_now_naive, onupdate=utc_now_naive
    )


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    value_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    scalar_value: Mapped[float | None] = mapped_column(nullable=True)
    systolic: Mapped[float | None] = mapped_column(nullable=True)
    diastolic: Mapped[float | None] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    observed_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quality_flags_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    measurement_context_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    superseded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("observations.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)

    @property
    def value(self) -> dict[str, float | str]:
        if self.value_kind == "blood_pressure":
            return {
                "kind": "blood_pressure",
                "systolic": self.systolic or 0.0,
                "diastolic": self.diastolic or 0.0,
            }
        return {"kind": "scalar", "amount": self.scalar_value or 0.0}

    @property
    def quality_flags(self) -> list[str]:
        return json.loads(self.quality_flags_json)

    @property
    def measurement_context(self) -> dict | None:
        """Optional collection conditions; older records have explicitly unknown context."""
        value = json.loads(self.measurement_context_json or "{}")
        return value or None


class SymptomReport(Base):
    __tablename__ = "symptom_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    observed_offset_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supersedes_id: Mapped[str | None] = mapped_column(
        ForeignKey("symptom_reports.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    superseded_by_id: Mapped[str | None] = mapped_column(
        ForeignKey("symptom_reports.id", ondelete="RESTRICT"), nullable=True, unique=True
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    withdrawal_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    actor: Mapped[str] = mapped_column(String(80), nullable=False, default="local_demo_operator")
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(40), nullable=False)
    object_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    related_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class IngestionRecord(Base):
    """A non-sensitive quarantine record; raw input is deliberately not persisted."""

    __tablename__ = "ingestion_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="quarantined")
    reason: Mapped[str] = mapped_column(String(300), nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ScenarioRun(Base):
    """Provenance for reproducible synthetic-data generation, never a clinical result."""

    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_id: Mapped[str] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    scenario: Mapped[str] = mapped_column(String(60), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    generator_version: Mapped[str] = mapped_column(String(40), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    event_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    declared_urgent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rule_set_version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    facts_json: Mapped[str] = mapped_column(Text, nullable=False)
    findings_json: Mapped[str] = mapped_column(Text, nullable=False)
    guidance_json: Mapped[str] = mapped_column(Text, nullable=False)
    hypotheses_json: Mapped[str] = mapped_column(Text, nullable=False)
    unknowns_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ChatMessage(Base):
    """One local assistant turn, linked to the source complaint and calculation."""

    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_report_id: Mapped[str | None] = mapped_column(ForeignKey("symptom_reports.id", ondelete="RESTRICT"), nullable=True)
    analysis_result_id: Mapped[str | None] = mapped_column(ForeignKey("analysis_results.id", ondelete="RESTRICT"), nullable=True)
    citations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    engine: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class ChatMemory(Base):
    __tablename__ = "chat_memory"
    crew_member_id: Mapped[str] = mapped_column(ForeignKey("crew_members.id"), primary_key=True)
    content_json: Mapped[str] = mapped_column(Text, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    analysis_result_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(
        ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    metric: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    horizon_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    method: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    predicted_value: Mapped[float | None] = mapped_column(nullable=True)
    interval_low: Mapped[float | None] = mapped_column(nullable=True)
    interval_high: Mapped[float | None] = mapped_column(nullable=True)
    training_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_mae: Mapped[float | None] = mapped_column(nullable=True)
    interval_coverage: Mapped[float | None] = mapped_column(nullable=True)
    input_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    insufficiency_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class PsychologicalAssessment(Base):
    __tablename__ = "psychological_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    instrument: Mapped[str] = mapped_column(String(80), nullable=False)
    mood: Mapped[float | None] = mapped_column(nullable=True)
    stress: Mapped[float | None] = mapped_column(nullable=True)
    fatigue: Mapped[float | None] = mapped_column(nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class EnvironmentalMeasurement(Base):
    __tablename__ = "environmental_measurements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_id: Mapped[str] = mapped_column(ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False)
    crew_member_id: Mapped[str | None] = mapped_column(ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=True, index=True)
    metric: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    value: Mapped[float] = mapped_column(nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    synthetic: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class WhatIfScenario(Base):
    __tablename__ = "what_if_scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)


class EmergencyHandoff(Base):
    __tablename__ = "emergency_handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    crew_member_id: Mapped[str] = mapped_column(ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="operator_declared")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SyncEvent(Base):
    __tablename__ = "sync_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now_naive)
