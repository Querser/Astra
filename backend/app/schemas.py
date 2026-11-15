"""Versioned API contracts for Stage 2 records."""

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal, Union
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator


class SourceType(str, Enum):
    MANUAL = "manual"
    SYNTHETIC = "synthetic"
    IMPORT = "import"
    SENSOR = "sensor"


class Metric(str, Enum):
    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE = "blood_pressure"
    SPO2 = "spo2"
    BODY_TEMPERATURE = "body_temperature"
    RESPIRATORY_RATE = "respiratory_rate"
    SLEEP_DURATION = "sleep_duration"
    SLEEP_QUALITY = "sleep_quality"
    ACTIVITY = "activity"
    EXERTION_FATIGUE = "exertion_fatigue"
    LAB_VALUE = "lab_value"


class ScenarioKind(str, Enum):
    NORMAL = "normal"
    GRADUAL_CHANGE = "gradual_change"
    MISSING_OR_CORRUPT = "missing_or_corrupt"
    OPERATOR_DECLARED_URGENT = "operator_declared_urgent"


def require_aware_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a timezone offset.")
    return value


def restore_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class CrewCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)
    fictional: Literal[True] = True

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Display name must not be blank.")
        return cleaned


class CrewUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=80)

    @field_validator("display_name")
    @classmethod
    def strip_display_name(cls, value: str) -> str:
        return CrewCreate.strip_display_name(value)


class CrewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    fictional: bool
    mission_location: str | None = None
    mission_phase: str | None = None
    habitat: str | None = None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    _normalize_dates = field_validator("archived_at", "created_at", "updated_at", mode="before")(restore_utc)


class MissionContextUpdate(BaseModel):
    mission_location: Literal["iss", "moon", "mars"]
    mission_phase: Literal["orbit", "surface"]
    habitat: str = Field(min_length=2, max_length=80)

    @model_validator(mode="after")
    def validate_location_phase(self) -> "MissionContextUpdate":
        if (self.mission_location == "iss") != (self.mission_phase == "orbit"):
            raise ValueError("ISS uses orbit; Moon and Mars use surface in this demo.")
        return self


class DataSourceCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    source_type: SourceType
    version: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Title must not be blank.")
        return cleaned


class DataSourceRead(DataSourceCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime

    _normalize_dates = field_validator("created_at", mode="before")(restore_utc)


class ScalarValue(BaseModel):
    kind: Literal["scalar"]
    amount: FiniteFloat


class BloodPressureValue(BaseModel):
    kind: Literal["blood_pressure"]
    systolic: FiniteFloat
    diastolic: FiniteFloat


ObservationValue = Annotated[
    Union[ScalarValue, BloodPressureValue], Field(discriminator="kind")
]


class MeasurementContext(BaseModel):
    """How a reading was collected; all fields remain optional for older records."""

    method: str | None = Field(default=None, max_length=120)
    device: str | None = Field(default=None, max_length=120)
    site: str | None = Field(default=None, max_length=80)
    activity_state: str | None = Field(default=None, max_length=80)
    posture: str | None = Field(default=None, max_length=80)
    mission_phase: str | None = Field(default=None, max_length=80)
    habitat: str | None = Field(default=None, max_length=120)
    subjective: bool | None = None
    baseline_status: Literal["unknown", "candidate", "approved"] | None = None
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("method", "device", "site", "activity_state", "posture", "mission_phase", "habitat", "notes")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ObservationData(BaseModel):
    metric: Metric
    value: ObservationValue
    unit: str = Field(min_length=1, max_length=40)
    observed_at: datetime
    source_id: UUID
    synthetic: bool
    quality_flags: list[str] = Field(default_factory=list, max_length=20)
    measurement_context: MeasurementContext | None = None

    @field_validator("unit")
    @classmethod
    def strip_unit(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Unit must not be blank.")
        return cleaned

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @field_validator("quality_flags")
    @classmethod
    def validate_flags(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value for value in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("Quality flags must be non-empty and unique.")
        return cleaned

    @model_validator(mode="after")
    def metric_matches_value(self) -> "ObservationData":
        if self.metric == Metric.BLOOD_PRESSURE and self.value.kind != "blood_pressure":
            raise ValueError("blood_pressure requires a blood_pressure value.")
        if self.metric != Metric.BLOOD_PRESSURE and self.value.kind != "scalar":
            raise ValueError("Only blood_pressure accepts a blood_pressure value.")
        return self


class ObservationCreate(ObservationData):
    crew_member_id: UUID


class ManualObservationCreate(BaseModel):
    crew_member_id: UUID
    metric: Metric
    value: ObservationValue
    unit: str = Field(min_length=1, max_length=40)
    observed_at: datetime
    measurement_context: MeasurementContext | None = None

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)

    @model_validator(mode="after")
    def validate_value_shape(self) -> "ManualObservationCreate":
        if (self.metric == Metric.BLOOD_PRESSURE) != (self.value.kind == "blood_pressure"):
            raise ValueError("Value shape does not match metric.")
        if self.metric in {Metric.SLEEP_QUALITY, Metric.EXERTION_FATIGUE} and self.value.kind == "scalar" and not 0 <= self.value.amount <= 10:
            raise ValueError("ASTRA self-report scores must be within 0–10.")
        return self


class ObservationRead(ObservationData):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    crew_member_id: UUID
    observed_offset_minutes: int
    recorded_at: datetime
    supersedes_id: UUID | None
    superseded_by_id: UUID | None
    withdrawn_at: datetime | None
    withdrawal_reason: str | None

    _normalize_dates = field_validator("observed_at", "recorded_at", "withdrawn_at", mode="before")(restore_utc)


class SymptomData(BaseModel):
    description: str = Field(min_length=1, max_length=2000)
    observed_at: datetime
    source_id: UUID
    synthetic: bool

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Description must not be blank.")
        return cleaned

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class SymptomCreate(SymptomData):
    crew_member_id: UUID


class ManualComplaintCreate(BaseModel):
    crew_member_id: UUID
    description: str = Field(min_length=2, max_length=2000)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def validate_observed_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class SymptomRead(SymptomData):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    crew_member_id: UUID
    observed_offset_minutes: int
    recorded_at: datetime
    supersedes_id: UUID | None
    superseded_by_id: UUID | None
    withdrawn_at: datetime | None
    withdrawal_reason: str | None

    _normalize_dates = field_validator("observed_at", "recorded_at", "withdrawn_at", mode="before")(restore_utc)


class WithdrawalRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=300)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Withdrawal reason must not be blank.")
        return cleaned


class AuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    occurred_at: datetime
    actor: str
    action: str
    object_type: str
    object_id: UUID
    related_object_id: UUID | None

    _normalize_dates = field_validator("occurred_at", mode="before")(restore_utc)


class IngestionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    filename: str
    row_number: int
    status: str
    reason: str
    content_sha256: str
    created_at: datetime

    _normalize_dates = field_validator("created_at", mode="before")(restore_utc)


class CsvImportRequest(BaseModel):
    crew_member_id: UUID
    filename: str = Field(min_length=1, max_length=260)
    content: str = Field(min_length=1, max_length=500_000)
    source_title: str = Field(min_length=2, max_length=160)
    source_version: str | None = Field(default=None, max_length=80)

    @field_validator("filename", "source_title")
    @classmethod
    def strip_import_labels(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Import filename and source title must not be blank.")
        return cleaned


class CsvImportResult(BaseModel):
    source: DataSourceRead
    accepted_observations: int
    quarantined_rows: int


class ScenarioRunRequest(BaseModel):
    crew_member_id: UUID
    scenario: ScenarioKind
    seed: int = Field(ge=0, le=2_147_483_647)
    start_at: datetime = Field(default_factory=lambda: datetime(2030, 1, 1, tzinfo=timezone.utc))

    @field_validator("start_at")
    @classmethod
    def validate_start_at(cls, value: datetime) -> datetime:
        return require_aware_datetime(value)


class ScenarioRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    crew_member_id: UUID
    source_id: UUID
    scenario: ScenarioKind
    seed: int
    generator_version: str
    start_at: datetime
    event_fingerprint: str
    declared_urgent: bool
    created_at: datetime
    observation_ids: list[UUID] = Field(default_factory=list)
    symptom_ids: list[UUID] = Field(default_factory=list)
    quarantined_rows: int = 0

    _normalize_dates = field_validator("start_at", "created_at", mode="before")(restore_utc)


class AnalysisRunRequest(BaseModel):
    crew_member_id: UUID


class AnalysisResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    crew_member_id: UUID
    rule_set_version: str
    input_ids: list[UUID] = Field(default_factory=list)
    facts: list[dict] = Field(default_factory=list)
    findings: list[dict] = Field(default_factory=list)
    guidance: list[dict] = Field(default_factory=list)
    hypotheses: list[dict] = Field(default_factory=list)
    unknowns: list[dict] = Field(default_factory=list)
    parameter_assessments: list[dict] = Field(default_factory=list)
    integrated_report: dict | None = None
    created_at: datetime

    _normalize_dates = field_validator("created_at", mode="before")(restore_utc)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    analysis_result_id: UUID
    crew_member_id: UUID
    rule_id: str
    title: str
    explanation: str
    state: str
    acknowledged_at: datetime | None
    created_at: datetime

    _normalize_dates = field_validator("acknowledged_at", "created_at", mode="before")(restore_utc)


class AssistantExplainRequest(BaseModel):
    crew_member_id: UUID
    analysis_result_id: UUID
    question: str | None = Field(default=None, max_length=1000)


class ChatCreate(BaseModel):
    crew_member_id: UUID
    message: str = Field(min_length=1, max_length=2000)
    request_id: UUID | None = None


class AssistantResponse(BaseModel):
    status: Literal["available", "fallback", "unavailable", "insufficient_evidence"]
    answer: str
    citations: list[str] = Field(default_factory=list)
    model: str | None = None


class BaselineMetricRead(BaseModel):
    metric: Metric
    unit: str | None
    count: int
    median: float | None
    mad: float | None
    interpretation: str


class BaselineResponse(BaseModel):
    crew_member_id: UUID
    metrics: list[BaselineMetricRead]
    limitation: str


class ForecastRunRequest(BaseModel):
    crew_member_id: UUID
    metric: Metric


class ForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    crew_member_id: UUID
    metric: Metric
    horizon_hours: int
    status: str
    method: str | None
    unit: str | None
    predicted_value: float | None
    interval_low: float | None
    interval_high: float | None
    training_count: int
    evaluation_mae: float | None
    interval_coverage: float | None
    input_ids: list[UUID] = Field(default_factory=list)
    insufficiency_reason: str | None
    created_at: datetime
    history_start_at: datetime | None = None
    history_end_at: datetime | None = None
    excluded_count: int | None = None
    synthetic_count: int | None = None
    evaluation_count: int | None = None
    baseline_mae: float | None = None
    recent_values: list[float] = Field(default_factory=list)
    selection_mae: dict[str, float] = Field(default_factory=dict)

    _normalize_dates = field_validator("created_at", "history_start_at", "history_end_at", mode="before")(restore_utc)


class PsychologicalCreate(BaseModel):
    crew_member_id: UUID
    source_id: UUID
    instrument: Literal["self_report_unvalidated"] = "self_report_unvalidated"
    mood: float | None = Field(default=None, ge=0, le=10)
    stress: float | None = Field(default=None, ge=0, le=10)
    fatigue: float | None = Field(default=None, ge=0, le=10)
    observed_at: datetime
    synthetic: bool
    _aware = field_validator("observed_at")(require_aware_datetime)

class PsychologicalRead(PsychologicalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    _dates = field_validator("observed_at", "created_at", mode="before")(restore_utc)

class EnvironmentalCreate(BaseModel):
    source_id: UUID
    crew_member_id: UUID | None = None
    metric: Literal["co2", "air_temperature", "humidity", "radiation", "noise", "space_weather_context", "gravity_context", "workload"]
    value: FiniteFloat
    unit: str = Field(min_length=1, max_length=40)
    observed_at: datetime
    synthetic: bool
    _aware = field_validator("observed_at")(require_aware_datetime)

class EnvironmentalRead(EnvironmentalCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    _dates = field_validator("observed_at", "created_at", mode="before")(restore_utc)

class WhatIfCreate(BaseModel):
    crew_member_id: UUID
    name: str = Field(min_length=2, max_length=120)
    assumptions: dict[str, float | str | bool] = Field(min_length=1)

class WhatIfRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    crew_member_id: UUID
    name: str
    assumptions: dict
    result: dict
    created_at: datetime
    _dates = field_validator("created_at", mode="before")(restore_utc)

class HandoffCreate(BaseModel):
    crew_member_id: UUID
    reason: str = Field(min_length=2, max_length=500)

class HandoffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    crew_member_id: UUID
    reason: str
    status: str
    created_at: datetime
    acknowledged_at: datetime | None
    _dates = field_validator("created_at", "acknowledged_at", mode="before")(restore_utc)

class SyncEventCreate(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=100)
    event_type: str = Field(min_length=2, max_length=80)
    payload: dict = Field(default_factory=dict)

class SyncEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    idempotency_key: str
    event_type: str
    payload_sha256: str
    status: str
    attempts: int
    acknowledged_at: datetime | None
    created_at: datetime
    _dates = field_validator("acknowledged_at", "created_at", mode="before")(restore_utc)


class ClientEvent(BaseModel):
    code: Literal["api_failure", "ui_exception", "scenario_failure", "form_failure"]
    request_id: str | None = Field(default=None, max_length=80)
