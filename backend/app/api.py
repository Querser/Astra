"""Stage 2 CRUD API for fictional, local demonstration records."""

import json
import hashlib
import re
from datetime import datetime, timezone
from threading import Lock
from typing import Iterator
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Database
from app.analytics import RULE_SET_VERSION, analyze_observations
from app.assistant import LocalAssistant, REFERENCE_CITATION
from app.chat_engine import reply_to_message
from app.smart_chat import respond
from app.chat_turn import SUMMARY, YES_NO
from app.chat_retrieval import space_science_cards
from app.dialogue_memory import advance, delivered, resolved_complaint
from app.forecasting import HORIZONS, baseline_profile, forecast_series, scalar_series
from app.mission_context import mission_context_for
from app.mission_readiness import assess_mission_readiness
from app.complaint_parser import explicit_measurements, symptom_codes
from app.ingest import parse_observation_csv
from app.models import (
    AuditEvent,
    Alert,
    AnalysisResult,
    ChatMessage,
    ChatMemory,
    CrewMember,
    DataSource,
    IngestionRecord,
    Observation,
    Forecast,
    EmergencyHandoff,
    EnvironmentalMeasurement,
    PsychologicalAssessment,
    SyncEvent,
    WhatIfScenario,
    ScenarioRun,
    SymptomReport,
    utc_now_naive,
)
from app.schemas import (
    AuditEventRead,
    AlertRead,
    AnalysisResultRead,
    AnalysisRunRequest,
    AssistantExplainRequest,
    ChatCreate,
    AssistantResponse,
    BaselineMetricRead,
    BaselineResponse,
    CrewCreate,
    CrewRead,
    CrewUpdate,
    MissionContextUpdate,
    ClientEvent,
    CsvImportRequest,
    CsvImportResult,
    DataSourceCreate,
    DataSourceRead,
    IngestionRecordRead,
    ObservationCreate,
    ManualObservationCreate,
    ManualComplaintCreate,
    ObservationData,
    ObservationRead,
    ForecastRead,
    ForecastRunRequest,
    EnvironmentalCreate,
    EnvironmentalRead,
    HandoffCreate,
    HandoffRead,
    PsychologicalCreate,
    PsychologicalRead,
    SyncEventCreate,
    SyncEventRead,
    WhatIfCreate,
    WhatIfRead,
    SymptomCreate,
    SymptomData,
    SymptomRead,
    ScenarioRunRead,
    ScenarioRunRequest,
    WithdrawalRequest,
)
from app.synthetic import GENERATOR_VERSION, generate_scenario

router = APIRouter()


@router.get("/reference/space-science", tags=["reference"])
def list_space_science() -> list[dict]:
    """Local, source-attributed scientific cards; no runtime network request."""
    return list(space_science_cards())


@router.post("/client-events", status_code=status.HTTP_204_NO_CONTENT, tags=["system"])
def record_client_event(payload: ClientEvent, request: Request) -> Response:
    """Accept a small allowlist of browser event codes, never free text or health data."""

    logger = getattr(request.app.state, "diagnostics", None)
    if logger is not None:
        logger.warning("client_event", extra={"code": payload.code, "request_id": payload.request_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def get_session(request: Request) -> Iterator[Session]:
    """Provide one session per request from the app-owned database."""

    database: Database = request.app.state.database
    yield from database.session()


def not_found(object_type: str, object_id: UUID) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{object_type} {object_id} was not found.")


def get_crew(session: Session, crew_id: UUID) -> CrewMember:
    crew = session.get(CrewMember, str(crew_id))
    if crew is None:
        raise not_found("Crew member", crew_id)
    return crew


def get_source(session: Session, source_id: UUID) -> DataSource:
    source = session.get(DataSource, str(source_id))
    if source is None:
        raise not_found("Data source", source_id)
    return source


def get_observation(session: Session, observation_id: UUID) -> Observation:
    observation = session.get(Observation, str(observation_id))
    if observation is None:
        raise not_found("Observation", observation_id)
    return observation


def get_symptom(session: Session, symptom_id: UUID) -> SymptomReport:
    symptom = session.get(SymptomReport, str(symptom_id))
    if symptom is None:
        raise not_found("Symptom report", symptom_id)
    return symptom


def audit(
    session: Session,
    action: str,
    object_type: str,
    object_id: str,
    related_object_id: str | None = None,
) -> None:
    """Record identifiers and action only; raw health values never enter the audit log."""

    session.add(
        AuditEvent(
            action=action,
            object_type=object_type,
            object_id=object_id,
            related_object_id=related_object_id,
        )
    )


def utc_storage(value: datetime) -> tuple[datetime, int]:
    """Store a UTC instant and preserve the source offset separately for display/audit."""

    offset = value.utcoffset()
    offset_minutes = int(offset.total_seconds() / 60) if offset else 0
    return value.astimezone(timezone.utc).replace(tzinfo=None), offset_minutes


def reject_archived_crew(crew: CrewMember) -> None:
    if crew.archived_at is not None:
        raise HTTPException(status_code=409, detail="Archived crew members cannot receive new records.")


def require_automated_ingestion(request: Request) -> None:
    if not request.app.state.automated_ingestion_enabled:
        raise HTTPException(status_code=403, detail="Automated ingestion is disabled in manual-entry mode.")


def manual_source(session: Session) -> DataSource:
    source = session.scalar(
        select(DataSource).where(
            DataSource.source_type == "manual",
            DataSource.title == "Manual entry",
        ).order_by(DataSource.created_at).limit(1)
    )
    if source is None:
        source = DataSource(
            title="Manual entry",
            source_type="manual",
            version="1",
            description="Entered by the local operator; no external sensor or file import.",
        )
        session.add(source)
        session.flush()
        audit(session, "data_source.created", "data_source", source.id)
    return source


def observation_from_data(
    crew_id: str, data: ObservationData, supersedes_id: str | None = None
) -> Observation:
    observed_at, offset_minutes = utc_storage(data.observed_at)
    value = data.value
    return Observation(
        crew_member_id=crew_id,
        source_id=str(data.source_id),
        metric=data.metric.value,
        value_kind=value.kind,
        scalar_value=value.amount if value.kind == "scalar" else None,
        systolic=value.systolic if value.kind == "blood_pressure" else None,
        diastolic=value.diastolic if value.kind == "blood_pressure" else None,
        unit=data.unit,
        observed_at=observed_at,
        observed_offset_minutes=offset_minutes,
        synthetic=data.synthetic,
        quality_flags_json=json.dumps(data.quality_flags, separators=(",", ":")),
        measurement_context_json=json.dumps(
            data.measurement_context.model_dump(exclude_none=True) if data.measurement_context else {},
            ensure_ascii=False, separators=(",", ":"),
        ),
        supersedes_id=supersedes_id,
    )


def symptom_from_data(crew_id: str, data: SymptomData, supersedes_id: str | None = None) -> SymptomReport:
    observed_at, offset_minutes = utc_storage(data.observed_at)
    return SymptomReport(
        crew_member_id=crew_id,
        source_id=str(data.source_id),
        description=data.description,
        observed_at=observed_at,
        observed_offset_minutes=offset_minutes,
        synthetic=data.synthetic,
        supersedes_id=supersedes_id,
    )


def scenario_response(
    run: ScenarioRun,
    observation_ids: list[str],
    symptom_ids: list[str],
    quarantined_rows: int,
) -> ScenarioRunRead:
    return ScenarioRunRead.model_validate(run).model_copy(
        update={
            "observation_ids": [UUID(item) for item in observation_ids],
            "symptom_ids": [UUID(item) for item in symptom_ids],
            "quarantined_rows": quarantined_rows,
        }
    )


def json_list(value: str) -> list:
    return json.loads(value)


def analysis_response(result: AnalysisResult) -> AnalysisResultRead:
    facts = json_list(result.facts_json)
    return AnalysisResultRead.model_validate(result).model_copy(
        update={
            "input_ids": [UUID(item) for item in json_list(result.input_ids_json)],
            "facts": facts,
            "findings": json_list(result.findings_json),
            "guidance": json_list(result.guidance_json),
            "hypotheses": json_list(result.hypotheses_json),
            "unknowns": json_list(result.unknowns_json),
            "parameter_assessments": [
                {key: value for key, value in item.items() if key != "kind"}
                for item in facts if item.get("kind") == "parameter_assessment"
            ],
            "integrated_report": next((
                {key: value for key, value in item.items() if key != "kind"}
                for item in facts if item.get("kind") == "integrated_report"
            ), None),
        }
    )


def forecast_response(forecast: Forecast) -> ForecastRead:
    return ForecastRead.model_validate(forecast).model_copy(
        update={"input_ids": [UUID(item) for item in json_list(forecast.input_ids_json)]}
    )

def what_if_response(item: WhatIfScenario) -> WhatIfRead:
    return WhatIfRead(
        id=item.id,
        crew_member_id=item.crew_member_id,
        name=item.name,
        assumptions=json.loads(item.assumptions_json),
        result=json.loads(item.result_json),
        created_at=item.created_at,
    )


def current_observations(session: Session, crew_id: str, metric: str | None = None) -> list[Observation]:
    statement = select(Observation).where(
        Observation.crew_member_id == crew_id,
        Observation.withdrawn_at.is_(None),
        Observation.superseded_by_id.is_(None),
    )
    if metric is not None:
        statement = statement.where(Observation.metric == metric)
    return list(session.scalars(statement.order_by(Observation.observed_at, Observation.id)))


@router.post("/crew", response_model=CrewRead, status_code=status.HTTP_201_CREATED, tags=["crew"])
def create_crew(payload: CrewCreate, session: Session = Depends(get_session)) -> CrewMember:
    crew = CrewMember(display_name=payload.display_name, fictional=payload.fictional)
    session.add(crew)
    session.flush()
    audit(session, "crew.created", "crew_member", crew.id)
    session.commit()
    session.refresh(crew)
    return crew


@router.get("/crew", response_model=list[CrewRead], tags=["crew"])
def list_crew(
    include_archived: bool = False,
    session: Session = Depends(get_session),
) -> list[CrewMember]:
    statement = select(CrewMember).order_by(CrewMember.created_at)
    if not include_archived:
        statement = statement.where(CrewMember.archived_at.is_(None))
    return list(session.scalars(statement))


@router.get("/crew/{crew_id}", response_model=CrewRead, tags=["crew"])
def read_crew(crew_id: UUID, session: Session = Depends(get_session)) -> CrewMember:
    return get_crew(session, crew_id)


@router.patch("/crew/{crew_id}/mission", response_model=CrewRead, tags=["crew"])
def update_mission(crew_id: UUID, payload: MissionContextUpdate, session: Session = Depends(get_session)) -> CrewMember:
    crew = get_crew(session, crew_id)
    reject_archived_crew(crew)
    crew.mission_location = payload.mission_location
    crew.mission_phase = payload.mission_phase
    crew.habitat = payload.habitat.strip()
    audit(session, "crew.mission_updated", "crew_member", crew.id)
    session.commit()
    session.refresh(crew)
    return crew


@router.patch("/crew/{crew_id}", response_model=CrewRead, tags=["crew"])
def update_crew(
    crew_id: UUID, payload: CrewUpdate, session: Session = Depends(get_session)
) -> CrewMember:
    crew = get_crew(session, crew_id)
    crew.display_name = payload.display_name
    audit(session, "crew.updated", "crew_member", crew.id)
    session.commit()
    session.refresh(crew)
    return crew


@router.delete("/crew/{crew_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["crew"])
def archive_crew(crew_id: UUID, session: Session = Depends(get_session)) -> Response:
    """Archive a profile so its observed history remains auditable."""

    crew = get_crew(session, crew_id)
    if crew.archived_at is None:
        crew.archived_at = utc_now_naive()
        audit(session, "crew.archived", "crew_member", crew.id)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/data-sources", response_model=DataSourceRead, status_code=status.HTTP_201_CREATED, tags=["sources"]
)
def create_data_source(
    payload: DataSourceCreate, request: Request, session: Session = Depends(get_session)
) -> DataSource:
    require_automated_ingestion(request)
    source = DataSource(**payload.model_dump(mode="json"))
    session.add(source)
    session.flush()
    audit(session, "data_source.created", "data_source", source.id)
    session.commit()
    session.refresh(source)
    return source


@router.get("/data-sources", response_model=list[DataSourceRead], tags=["sources"])
def list_data_sources(session: Session = Depends(get_session)) -> list[DataSource]:
    return list(session.scalars(select(DataSource).order_by(DataSource.created_at)))


@router.post(
    "/synthetic-scenarios/runs",
    response_model=ScenarioRunRead,
    status_code=status.HTTP_201_CREATED,
    tags=["synthetic scenarios"],
)
def run_synthetic_scenario(
    payload: ScenarioRunRequest, request: Request, session: Session = Depends(get_session)
) -> ScenarioRunRead:
    """Persist a seeded, explicitly synthetic demonstration scenario."""

    require_automated_ingestion(request)
    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    plan = generate_scenario(payload.scenario, payload.seed, payload.start_at)
    source = DataSource(
        title=f"Synthetic scenario: {payload.scenario.value} (seed {payload.seed})",
        source_type="synthetic",
        version=GENERATOR_VERSION,
        description="Generated locally for a non-clinical ASTRA demonstration.",
    )
    session.add(source)
    session.flush()

    observation_ids: list[str] = []
    symptom_ids: list[str] = []
    for generated in plan.observations:
        data = ObservationData.model_validate(
            {
                "metric": generated.metric,
                "value": generated.value,
                "unit": generated.unit,
                "observed_at": generated.observed_at,
                "source_id": source.id,
                "synthetic": True,
                "quality_flags": generated.quality_flags,
            }
        )
        observation = observation_from_data(crew.id, data)
        session.add(observation)
        session.flush()
        observation_ids.append(observation.id)

    for generated in plan.symptoms:
        data = SymptomData.model_validate(
            {
                "description": generated.description,
                "observed_at": generated.observed_at,
                "source_id": source.id,
                "synthetic": True,
            }
        )
        symptom = symptom_from_data(crew.id, data)
        session.add(symptom)
        session.flush()
        symptom_ids.append(symptom.id)

    for quarantined in plan.quarantines:
        session.add(
            IngestionRecord(
                source_id=source.id,
                filename=quarantined.filename,
                row_number=quarantined.row_number,
                status="quarantined",
                reason=quarantined.reason,
                content_sha256=quarantined.content_sha256,
            )
        )

    stored_start_at, _ = utc_storage(payload.start_at)
    run = ScenarioRun(
        crew_member_id=crew.id,
        source_id=source.id,
        scenario=payload.scenario.value,
        seed=payload.seed,
        generator_version=GENERATOR_VERSION,
        start_at=stored_start_at,
        event_fingerprint=plan.fingerprint(),
        declared_urgent=plan.declared_urgent,
    )
    session.add(run)
    session.flush()
    audit(session, "synthetic_scenario.run", "scenario_run", run.id, source.id)
    session.commit()
    session.refresh(run)
    return scenario_response(run, observation_ids, symptom_ids, len(plan.quarantines))


@router.post(
    "/imports/csv",
    response_model=CsvImportResult,
    status_code=status.HTTP_201_CREATED,
    tags=["imports"],
)
def import_csv(payload: CsvImportRequest, request: Request, session: Session = Depends(get_session)) -> CsvImportResult:
    """Import structurally valid rows and quarantine invalid rows without retaining raw CSV."""

    require_automated_ingestion(request)
    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    source = DataSource(
        title=payload.source_title,
        source_type="import",
        version=payload.source_version,
        description="CSV import provenance; raw source content is not stored in quarantine records.",
    )
    session.add(source)
    session.flush()
    parsed = parse_observation_csv(payload.content, source.id)
    for data in parsed.observations:
        observation = observation_from_data(crew.id, data)
        session.add(observation)
        session.flush()
        audit(session, "observation.imported", "observation", observation.id, source.id)
    for quarantined in parsed.quarantined_rows:
        session.add(
            IngestionRecord(
                source_id=source.id,
                filename=payload.filename,
                row_number=quarantined.row_number,
                status="quarantined",
                reason=quarantined.reason,
                content_sha256=quarantined.content_sha256,
            )
        )
    audit(session, "csv_import.completed", "data_source", source.id)
    session.commit()
    session.refresh(source)
    return CsvImportResult(
        source=DataSourceRead.model_validate(source),
        accepted_observations=len(parsed.observations),
        quarantined_rows=len(parsed.quarantined_rows),
    )


@router.post(
    "/manual/observations",
    response_model=ObservationRead,
    status_code=status.HTTP_201_CREATED,
    tags=["observations"],
)
def create_manual_observation(
    payload: ManualObservationCreate, session: Session = Depends(get_session)
) -> Observation:
    """Store a human-entered observation with internal provenance."""

    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    source = manual_source(session)
    data = ObservationData.model_validate(
        {
            **payload.model_dump(mode="python"),
            "source_id": source.id,
            "synthetic": False,
            "quality_flags": [],
        }
    )
    observation = observation_from_data(crew.id, data)
    session.add(observation)
    session.flush()
    audit(session, "observation.created", "observation", observation.id, crew.id)
    session.commit()
    session.refresh(observation)
    return observation


@router.post(
    "/observations", response_model=ObservationRead, status_code=status.HTTP_201_CREATED, tags=["observations"]
)
def create_observation(
    payload: ObservationCreate, request: Request, session: Session = Depends(get_session)
) -> Observation:
    require_automated_ingestion(request)
    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    get_source(session, payload.source_id)
    observation = observation_from_data(crew.id, payload)
    session.add(observation)
    session.flush()
    audit(session, "observation.created", "observation", observation.id)
    session.commit()
    session.refresh(observation)
    return observation


@router.get("/observations", response_model=list[ObservationRead], tags=["observations"])
def list_observations(
    crew_member_id: UUID | None = None,
    include_withdrawn: bool = False,
    current_only: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[Observation]:
    statement = select(Observation).order_by(Observation.observed_at.desc()).limit(limit)
    if crew_member_id is not None:
        statement = statement.where(Observation.crew_member_id == str(crew_member_id))
    if not include_withdrawn:
        statement = statement.where(Observation.withdrawn_at.is_(None))
    if current_only:
        statement = statement.where(Observation.superseded_by_id.is_(None))
    return list(session.scalars(statement))


@router.get("/observations/{observation_id}", response_model=ObservationRead, tags=["observations"])
def read_observation(observation_id: UUID, session: Session = Depends(get_session)) -> Observation:
    return get_observation(session, observation_id)


@router.patch(
    "/observations/{observation_id}", response_model=ObservationRead, status_code=status.HTTP_201_CREATED, tags=["observations"]
)
def revise_observation(
    observation_id: UUID, payload: ObservationData, request: Request, session: Session = Depends(get_session)
) -> Observation:
    previous = get_observation(session, observation_id)
    if previous.withdrawn_at is not None or previous.superseded_by_id is not None:
        raise HTTPException(status_code=409, detail="Only a current active observation can be revised.")
    source = get_source(session, payload.source_id)
    if payload.synthetic or source.source_type != "manual":
        require_automated_ingestion(request)
    if payload.measurement_context is None and previous.measurement_context is not None:
        payload = ObservationData.model_validate({
            **payload.model_dump(), "measurement_context": previous.measurement_context,
        })
    revision = observation_from_data(previous.crew_member_id, payload, supersedes_id=previous.id)
    session.add(revision)
    session.flush()
    previous.superseded_by_id = revision.id
    audit(session, "observation.revised", "observation", revision.id, previous.id)
    session.commit()
    session.refresh(revision)
    return revision


@router.delete("/observations/{observation_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["observations"])
def withdraw_observation(
    observation_id: UUID,
    payload: WithdrawalRequest,
    session: Session = Depends(get_session),
) -> Response:
    observation = get_observation(session, observation_id)
    if observation.withdrawn_at is None:
        observation.withdrawn_at = utc_now_naive()
        observation.withdrawal_reason = payload.reason
        audit(session, "observation.withdrawn", "observation", observation.id)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/symptoms", response_model=SymptomRead, status_code=status.HTTP_201_CREATED, tags=["symptoms"])
def create_symptom(payload: SymptomCreate, request: Request, session: Session = Depends(get_session)) -> SymptomReport:
    require_automated_ingestion(request)
    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    get_source(session, payload.source_id)
    symptom = symptom_from_data(crew.id, payload)
    session.add(symptom)
    session.flush()
    audit(session, "symptom.created", "symptom_report", symptom.id)
    session.commit()
    session.refresh(symptom)
    return symptom


@router.post("/manual/complaints", status_code=status.HTTP_201_CREATED, tags=["symptoms"])
def create_manual_complaint(payload: ManualComplaintCreate, session: Session = Depends(get_session)) -> dict:
    """Store local Russian complaint and only explicitly labeled numerical readings."""
    crew = get_crew(session, payload.crew_member_id)
    reject_archived_crew(crew)
    source = manual_source(session)
    observed_at, offset = utc_storage(payload.observed_at)
    description = payload.description.strip()
    complaint = SymptomReport(
        crew_member_id=crew.id, source_id=source.id, description=description,
        observed_at=observed_at, observed_offset_minutes=offset, synthetic=False,
    )
    session.add(complaint)
    session.flush()
    observations = save_reported_measurements(session, crew.id, description, observed_at, offset, source.id)
    audit(session, "complaint.created", "symptom_report", complaint.id, crew.id)
    session.commit()
    return {
        "symptom_report_id": complaint.id,
        "recognized_symptom_codes": symptom_codes(description),
        "parsed_measurements": [{"id": item.id, "metric": item.metric, "value": item.value, "unit": item.unit} for item in observations],
    }


def save_reported_measurements(session, crew_id, description, observed_at, offset, source_id=None, *, parsed=None):
    observations = []
    for item in explicit_measurements(description) if parsed is None else parsed:
        source_id = source_id or manual_source(session).id
        observation = Observation(
            crew_member_id=crew_id, source_id=source_id, metric=item["metric"],
            value_kind=item["value_kind"], scalar_value=item.get("scalar_value"),
            systolic=item.get("systolic"), diastolic=item.get("diastolic"),
            unit=item["unit"], observed_at=observed_at, observed_offset_minutes=offset,
            synthetic=False, quality_flags_json="[]",
        )
        session.add(observation)
        observations.append(observation)
    session.flush()
    return observations


@router.get("/symptoms", response_model=list[SymptomRead], tags=["symptoms"])
def list_symptoms(
    crew_member_id: UUID | None = None,
    include_withdrawn: bool = False,
    limit: int = Query(default=50, ge=1, le=100),
    session: Session = Depends(get_session),
) -> list[SymptomReport]:
    statement = select(SymptomReport).order_by(SymptomReport.observed_at.desc()).limit(limit)
    if crew_member_id is not None:
        statement = statement.where(SymptomReport.crew_member_id == str(crew_member_id))
    if not include_withdrawn:
        statement = statement.where(SymptomReport.withdrawn_at.is_(None))
    return list(session.scalars(statement))


@router.get("/symptoms/{symptom_id}", response_model=SymptomRead, tags=["symptoms"])
def read_symptom(symptom_id: UUID, session: Session = Depends(get_session)) -> SymptomReport:
    return get_symptom(session, symptom_id)


@router.patch("/symptoms/{symptom_id}", response_model=SymptomRead, status_code=status.HTTP_201_CREATED, tags=["symptoms"])
def revise_symptom(
    symptom_id: UUID, payload: SymptomData, session: Session = Depends(get_session)
) -> SymptomReport:
    previous = get_symptom(session, symptom_id)
    if previous.withdrawn_at is not None or previous.superseded_by_id is not None:
        raise HTTPException(status_code=409, detail="Only a current active symptom report can be revised.")
    get_source(session, payload.source_id)
    revision = symptom_from_data(previous.crew_member_id, payload, supersedes_id=previous.id)
    session.add(revision)
    session.flush()
    previous.superseded_by_id = revision.id
    audit(session, "symptom.revised", "symptom_report", revision.id, previous.id)
    session.commit()
    session.refresh(revision)
    return revision


@router.delete("/symptoms/{symptom_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["symptoms"])
def withdraw_symptom(
    symptom_id: UUID,
    payload: WithdrawalRequest,
    session: Session = Depends(get_session),
) -> Response:
    symptom = get_symptom(session, symptom_id)
    if symptom.withdrawn_at is None:
        symptom.withdrawn_at = utc_now_naive()
        symptom.withdrawal_reason = payload.reason
        audit(session, "symptom.withdrawn", "symptom_report", symptom.id)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/audit-events", response_model=list[AuditEventRead], tags=["audit"])
def list_audit_events(
    object_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[AuditEvent]:
    statement = select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(limit)
    if object_id is not None:
        statement = statement.where(AuditEvent.object_id == str(object_id))
    return list(session.scalars(statement))


@router.get("/ingestion-records", response_model=list[IngestionRecordRead], tags=["imports"])
def list_ingestion_records(
    source_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    session: Session = Depends(get_session),
) -> list[IngestionRecord]:
    statement = select(IngestionRecord).order_by(IngestionRecord.created_at.desc()).limit(limit)
    if source_id is not None:
        statement = statement.where(IngestionRecord.source_id == str(source_id))
    return list(session.scalars(statement))


@router.post("/analysis/run", response_model=AnalysisResultRead, status_code=status.HTTP_201_CREATED, tags=["analysis"])
def run_analysis(
    payload: AnalysisRunRequest, response: Response, session: Session = Depends(get_session)
) -> AnalysisResultRead:
    """Persist a deterministic analysis that remains independent of the LLM."""

    crew = get_crew(session, payload.crew_member_id)
    observations = current_observations(session, crew.id)
    symptom_rows = list(session.scalars(
        select(SymptomReport).where(
            SymptomReport.crew_member_id == crew.id,
            SymptomReport.withdrawn_at.is_(None),
            SymptomReport.superseded_by_id.is_(None),
        ).order_by(SymptomReport.observed_at, SymptomReport.id)
    ))
    resolved_report_ids = {
        episode.get("source_report_id")
        for episode in stored_memory(session, crew.id).get("medical_history", [])
        if episode.get("status") == "resolved_by_user_report"
    }
    symptom_rows = [row for row in symptom_rows if row.id not in resolved_report_ids]
    source_ids = {item.source_id for item in observations} | {item.source_id for item in symptom_rows}
    sources = {
        item.id: item
        for item in session.scalars(select(DataSource).where(DataSource.id.in_(source_ids)))
    } if source_ids else {}
    source_types = {key: value.source_type for key, value in sources.items()}
    symptom_reports = [{
        "id": item.id,
        "description": item.description,
        "observed_at": item.observed_at.isoformat() + "Z",
        "recorded_at": item.recorded_at.isoformat() + "Z",
        "source_id": item.source_id,
        "source_type": sources[item.source_id].source_type if item.source_id in sources else "unknown",
        "source_title": sources[item.source_id].title if item.source_id in sources else "Unknown source",
        "synthetic": item.synthetic,
    } for item in symptom_rows]
    environment_rows = list(session.scalars(
        select(EnvironmentalMeasurement).where(EnvironmentalMeasurement.crew_member_id == crew.id).order_by(
            EnvironmentalMeasurement.observed_at.desc(), EnvironmentalMeasurement.id.desc()
        ).limit(20)
    ))
    environment_records = [{
        "id": item.id, "metric": item.metric, "value": item.value,
        "unit": item.unit, "observed_at": item.observed_at.isoformat() + "Z",
        "synthetic": item.synthetic,
    } for item in environment_rows]
    plan = analyze_observations(
        observations,
        source_types=source_types,
        symptom_reports=symptom_reports,
        environment_records=environment_records,
        mission_context=mission_context_for(crew),
    )
    input_ids_json = json.dumps(plan.input_ids, separators=(",", ":"))
    facts_json = json.dumps(plan.facts, separators=(",", ":"))
    latest = session.scalar(
        select(AnalysisResult)
        .where(AnalysisResult.crew_member_id == crew.id)
        .order_by(AnalysisResult.created_at.desc(), AnalysisResult.id.desc())
        .limit(1)
    )
    if latest is not None and latest.rule_set_version == RULE_SET_VERSION and latest.input_ids_json == input_ids_json and latest.facts_json == facts_json:
        response.status_code = status.HTTP_200_OK
        return analysis_response(latest)
    result = AnalysisResult(
        crew_member_id=crew.id,
        rule_set_version=RULE_SET_VERSION,
        input_ids_json=input_ids_json,
        facts_json=facts_json,
        findings_json=json.dumps(plan.findings, separators=(",", ":")),
        guidance_json=json.dumps(plan.guidance, separators=(",", ":")),
        hypotheses_json=json.dumps(plan.hypotheses, separators=(",", ":")),
        unknowns_json=json.dumps(plan.unknowns, separators=(",", ":")),
    )
    session.add(result)
    session.flush()
    for candidate in plan.alerts:
        session.add(
            Alert(
                analysis_result_id=result.id,
                crew_member_id=crew.id,
                rule_id=candidate["rule_id"],
                title=candidate["title"],
                explanation=candidate["explanation"],
            )
        )
    audit(session, "analysis.completed", "analysis_result", result.id, crew.id)
    session.commit()
    session.refresh(result)
    return analysis_response(result)


@router.get("/analysis/{analysis_id}", response_model=AnalysisResultRead, tags=["analysis"])
def read_analysis(analysis_id: UUID, session: Session = Depends(get_session)) -> AnalysisResultRead:
    result = session.get(AnalysisResult, str(analysis_id))
    if result is None:
        raise not_found("Analysis result", analysis_id)
    return analysis_response(result)


@router.get("/alerts", response_model=list[AlertRead], tags=["analysis"])
def list_alerts(
    crew_member_id: UUID | None = None,
    session: Session = Depends(get_session),
) -> list[Alert]:
    statement = select(Alert).order_by(Alert.created_at.desc())
    if crew_member_id is not None:
        latest = session.scalar(
            select(AnalysisResult.id)
            .where(AnalysisResult.crew_member_id == str(crew_member_id))
            .order_by(AnalysisResult.created_at.desc(), AnalysisResult.id.desc())
            .limit(1)
        )
        if latest is None:
            return []
        statement = statement.where(Alert.analysis_result_id == latest)
    return list(session.scalars(statement))


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertRead, tags=["analysis"])
def acknowledge_alert(alert_id: UUID, session: Session = Depends(get_session)) -> Alert:
    alert = session.get(Alert, str(alert_id))
    if alert is None:
        raise not_found("Alert", alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = utc_now_naive()
        alert.state = "acknowledged"
        audit(session, "alert.acknowledged", "alert", alert.id)
        session.commit()
        session.refresh(alert)
    return alert


@router.post("/assistant/explain", response_model=AssistantResponse, tags=["assistant"])
def explain_analysis(
    payload: AssistantExplainRequest, request: Request, session: Session = Depends(get_session)
) -> AssistantResponse:
    result = session.get(AnalysisResult, str(payload.analysis_result_id))
    if result is None or result.crew_member_id != str(payload.crew_member_id):
        raise HTTPException(status_code=404, detail="Analysis result was not found for this crew profile.")
    analysis = analysis_response(result).model_dump(mode="json")
    assistant: LocalAssistant = request.app.state.local_assistant
    result_status, answer = assistant.explain(analysis, payload.question)
    source_citations = sorted({
        str(item["source_url"])
        for item in analysis["facts"]
        if item.get("kind") == "reference_review"
        and item.get("status") != "not_assessed"
        and item.get("source_url")
    } | {
        str(source["url"])
        for candidate in (analysis.get("integrated_report") or {}).get("diagnostic_candidates", [])
        for source in candidate.get("sources", []) if source.get("url")
    }) if result_status in {"fallback", "available"} else []
    return AssistantResponse(
        status=result_status,
        answer=answer,
        citations=[REFERENCE_CITATION, *source_citations],
        model=assistant.model if result_status == "available" else None,
    )


def chat_record(item: ChatMessage) -> dict:
    return {
        "id": item.id, "crew_member_id": item.crew_member_id, "role": item.role,
        "body": item.body, "source_report_id": item.source_report_id,
        "analysis_result_id": item.analysis_result_id,
        "citations": json.loads(item.citations_json),
        "created_at": item.created_at.isoformat() + "Z", "legacy": False,
        "engine": item.engine, "request_id": item.request_id,
    }


@router.get("/assistant/chat/{crew_id}", tags=["assistant"])
def get_chat(crew_id: UUID, session: Session = Depends(get_session)) -> list[dict]:
    """Include older manual complaints as history while keeping profile isolation."""
    crew = get_crew(session, crew_id)
    rows = list(session.scalars(select(ChatMessage).where(ChatMessage.crew_member_id == crew.id).order_by(ChatMessage.created_at, ChatMessage.id)))
    result = [chat_record(row) for row in rows]
    linked = {row.source_report_id for row in rows if row.source_report_id}
    legacy = session.scalars(select(SymptomReport).where(
        SymptomReport.crew_member_id == crew.id,
        SymptomReport.withdrawn_at.is_(None),
        SymptomReport.superseded_by_id.is_(None),
    ))
    for report in legacy:
        if report.id not in linked:
            result.append({
                "id": report.id, "crew_member_id": crew.id, "role": "user",
                "body": report.description, "source_report_id": report.id,
                "analysis_result_id": None, "citations": [],
                "created_at": report.observed_at.isoformat() + "Z", "legacy": True,
                "engine": None,
            })
    return sorted(result, key=lambda row: (row["created_at"], row["id"]))


def stored_memory(session: Session, crew_id: str) -> dict:
    row = session.get(ChatMemory, crew_id)
    if row:
        return json.loads(row.content_json)
    # Recover the active episode for profiles created before chat memory existed.
    rows = list(session.scalars(select(ChatMessage).where(ChatMessage.crew_member_id == crew_id)
                                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(40)))
    memory = {}
    for turn in reversed(rows):
        if turn.role == "user":
            memory = advance(memory, turn.id, turn.body)
        elif turn.engine and not turn.engine.startswith("local_model_error:"):
            memory = delivered(memory, turn.id, turn.body)
    return memory


def repair_legacy_recurrence(session: Session, crew_id: str, memory: dict) -> dict:
    """Split an older same-topic recurrence that was linked to a resolved report."""
    history = memory.get("medical_history") or []
    if not history or not history[-1].get("source_report_id"):
        return memory
    original_id = history[-1]["source_report_id"]
    original = session.get(SymptomReport, original_id)
    if original is None:
        return memory
    rows = list(reversed(list(session.scalars(select(ChatMessage).where(
        ChatMessage.crew_member_id == crew_id,
    ).order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(100)))))
    topic = history[-1].get("topic") or memory.get("topic") or "general"
    recurrence_index = None
    for index, row in enumerate(rows):
        if row.role != "user" or not resolved_complaint(row.body, topic) or row.created_at <= original.observed_at:
            continue
        later = next((position for position in range(index + 1, len(rows))
                      if rows[position].role == "user" and rows[position].source_report_id == original_id
                      and rows[position].created_at > row.created_at
                      and symptom_codes(rows[position].body)), None)
        if later is not None:
            recurrence_index = later
    if recurrence_index is None:
        return memory
    recurrence = rows[recurrence_index]
    history[-1]["status"] = "resolved_by_user_report"
    prior_symptoms = history[-1].get("symptoms") or []
    if recurrence.body in prior_symptoms:
        history[-1]["symptoms"] = prior_symptoms[:len(prior_symptoms) - 1 - prior_symptoms[::-1].index(recurrence.body)]
    report = SymptomReport(crew_member_id=crew_id, source_id=manual_source(session).id,
                           description=recurrence.body, observed_at=recurrence.created_at,
                           observed_offset_minutes=0, synthetic=False)
    session.add(report)
    session.flush()
    history.append({"source_report_id": report.id, "topic": topic, "symptoms": [],
                    "assessment": "", "helped": [], "status": "active"})
    replay = {"medical_history": history}
    last_kind = "other"
    for row in rows[recurrence_index:]:
        if row.role == "user":
            replay = advance(replay, row.id, row.body)
            last_kind = replay.get("last_update", {}).get("kind", "other")
            if last_kind not in {"summary", "greeting"}:
                row.source_report_id = report.id
                if replay["last_update"].get("keys") or symptom_codes(row.body):
                    replay["medical_history"][-1]["symptoms"].append(row.body)
                if re.search(r"приложил|помогл|полегчал|обработал|принял|выполняю|applied|helped|relieved|treated|took|taking", row.body, re.I):
                    replay["medical_history"][-1]["helped"].append(row.body)
                if last_kind in {"resolution", "resolution_confirmed"}:
                    replay["medical_history"][-1]["status"] = "resolved_by_user_report"
            else:
                row.source_report_id = None
        elif row.role == "assistant":
            row.source_report_id = report.id if last_kind not in {"summary", "greeting"} else None
            if row.engine and not row.engine.startswith("local_model_error:"):
                replay = delivered(replay, row.id, row.body)
                if last_kind not in {"summary", "greeting"}:
                    replay["medical_history"][-1]["assessment"] = row.body
                    replay["medical_history"][-1]["citations"] = json.loads(row.citations_json)
    audit(session, "chat.legacy_episode_repaired", "symptom_report", report.id, original_id)
    return replay


@router.get("/assistant/chat/{crew_id}/memory", tags=["assistant"])
def get_chat_memory(crew_id: UUID, session: Session = Depends(get_session)) -> dict:
    return stored_memory(session, get_crew(session, crew_id).id)


# The local API runs in a single process; allow distinct profiles to infer
# concurrently while turn order within one profile stays serial.
_crew_chat_locks = {}
_chat_lock_registry = Lock()


@router.post("/assistant/chat", status_code=status.HTTP_201_CREATED, tags=["assistant"])
def send_chat(payload: ChatCreate, request: Request, session: Session = Depends(get_session)) -> dict:
    crew = get_crew(session, payload.crew_member_id)
    crew_id = crew.id
    session.rollback()
    with _chat_lock_registry:
        lock = _crew_chat_locks.setdefault(crew_id, Lock())
    with lock:
        return process_chat(payload, request, session, crew_id)


def process_chat(payload: ChatCreate, request: Request, session: Session, crew_id: str) -> dict:
    request_id = str(payload.request_id or uuid4())
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="Write a message.")
    owned = select(ChatMessage).where(ChatMessage.crew_member_id == crew_id, ChatMessage.request_id == request_id)
    user_turn = session.scalar(owned.where(ChatMessage.role == "user"))
    if user_turn is not None:
        if user_turn.body != message:
            raise HTTPException(409, "The request identifier is already linked to another message.")
        assistant_turn = session.scalar(owned.where(ChatMessage.role == "assistant"))
        if assistant_turn is not None:
            previous = session.scalar(select(AnalysisResult).where(
                AnalysisResult.id == assistant_turn.analysis_result_id, AnalysisResult.crew_member_id == crew_id))
            if previous is None:
                raise HTTPException(409, "Cannot restore the saved result of the query.")
            return {"request_id": request_id, "crew_member_id": crew_id,
                    "messages": [chat_record(user_turn), chat_record(assistant_turn)],
                    "analysis": analysis_response(previous).model_dump(mode="json")}
    reject_archived_crew(get_crew(session, payload.crew_member_id))
    prior_dialogue = list(session.scalars(select(ChatMessage).where(
        ChatMessage.crew_member_id == crew_id, ChatMessage.id != (user_turn.id if user_turn else ""),
    ).order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc()).limit(10)))
    memory = stored_memory(session, crew_id)
    if user_turn is None:
        memory = repair_legacy_recurrence(session, crew_id, memory)
        history_items = memory.get("medical_history") or []
        recent_user = next((row.body for row in prior_dialogue if row.role == "user"), "")
        neck_active = any(f.get("key") == "neck_swelling" and f.get("value") is True and f.get("status") == "active"
                          for f in memory.get("facts", []))
        if (history_items and history_items[-1].get("status") == "active"
                and resolved_complaint(recent_user, memory.get("topic"))
                and (not neck_active or re.search(r"вс[её]\s+прошло|everything (?:is |has )?gone|all symptoms (?:are |have )?gone", recent_user, re.I))):
            history_items[-1]["status"] = "resolved_by_user_report"
            memory["episode_resolved"] = True
        user_turn = ChatMessage(crew_member_id=crew_id, role="user", body=message, request_id=request_id)
        session.add(user_turn)
        session.flush()
        memory = advance(memory, user_turn.id, message)
        clinical = bool(memory.get("last_update", {}).get("keys") or symptom_codes(message) or re.search(
            r"порез|ран[ауеы]|шея\s+опух|опухла\s+шея|болит\s+(?:рука|нога|спина|шея)|"
            r"\b(?:cut|wound|swollen neck|neck swelling|arm pain|leg pain|back pain)\b|\d+\s*/\s*10", message, re.I))
        history_items = memory.setdefault("medical_history", [])
        if clinical and (memory.get("last_update", {}).get("kind") == "new_topic" or not history_items):
            report = SymptomReport(crew_member_id=crew_id, source_id=manual_source(session).id,
                                   description=message, observed_at=user_turn.created_at,
                                   observed_offset_minutes=0, synthetic=False)
            session.add(report)
            session.flush()
            user_turn.source_report_id = report.id
            history_items.append({"source_report_id": report.id, "topic": memory.get("topic"),
                                  "symptoms": [message], "assessment": "", "helped": [], "status": "active"})
            audit(session, "complaint.from_chat", "symptom_report", report.id, user_turn.id)
        elif history_items and clinical:
            history_items[-1].setdefault("symptoms", []).append(message)
            user_turn.source_report_id = history_items[-1].get("source_report_id")
        elif history_items and memory.get("last_update", {}).get("kind") not in {"summary", "greeting"}:
            user_turn.source_report_id = history_items[-1].get("source_report_id")
        if history_items and re.search(r"приложил|помогл|полегчал|обработал|принял|выполняю|applied|helped|relieved|treated|took|taking", message, re.I):
            history_items[-1].setdefault("helped", []).append(message)
        if history_items and memory.get("last_update", {}).get("kind") == "resolution":
            history_items[-1]["status"] = "resolved_by_user_report"
        session.merge(ChatMemory(crew_member_id=crew_id, content_json=json.dumps(memory, ensure_ascii=False)))
        units = {"body_temperature": "°C", "heart_rate": "bpm", "sleep_duration": "h", "spo2": "%"}
        parsed = []
        for fact in memory.get("facts", []):
            if fact["user_message_id"] != user_turn.id or fact["status"] != "active" or fact["kind"] != "numeric":
                continue
            metric, value = fact["key"], fact["value"]
            if metric == "blood_pressure":
                parsed.append(dict(metric=metric, value_kind="blood_pressure", unit="mmHg", systolic=value[0], diastolic=value[1]))
            elif metric in units:
                parsed.append(dict(metric=metric, value_kind="scalar", unit=units[metric], scalar_value=value))
        for reading in save_reported_measurements(session, crew_id, message, user_turn.created_at, 0, parsed=parsed):
            audit(session, "observation.from_chat", "observation", reading.id, user_turn.id)
            if memory["last_update"]["kind"] == "correction":
                prior_fact = next((f for f in reversed(memory["facts"])
                                   if f["key"] == reading.metric and f.get("superseded_by") == user_turn.id), None)
                if prior_fact:
                    prior_reading = session.scalar(select(Observation).join(AuditEvent, AuditEvent.object_id == Observation.id).where(
                        Observation.crew_member_id == crew_id, Observation.metric == reading.metric,
                        Observation.superseded_by_id.is_(None), Observation.withdrawn_at.is_(None),
                        AuditEvent.action == "observation.from_chat",
                        AuditEvent.related_object_id == prior_fact["user_message_id"]))
                    if prior_reading:
                        prior_reading.superseded_by_id = reading.id
                        reading.supersedes_id = prior_reading.id
        audit(session, "chat.user_created", "chat_message", user_turn.id, crew_id)
        session.commit()
    elif any(item.created_at > user_turn.created_at for item in prior_dialogue):
        raise HTTPException(409, "After the interrupted query, a new dialogue began. The history is saved.")
    calculation = run_analysis(AnalysisRunRequest(crew_member_id=payload.crew_member_id), Response(), session)
    history = [{"role": item.role, "content": item.body, "id": item.id, "engine": item.engine,
                "citations": json.loads(item.citations_json) if item.role == "assistant" else []}
               for item in reversed(prior_dialogue)]
    topic_metric = {"oxygen": "spo2", "fever_headache": "body_temperature", "blood_pressure": "blood_pressure"}
    if SUMMARY.search(message) or memory.get("last_update", {}).get("kind") == "summary":
        measurements = current_observations(session, crew_id)
    elif memory.get("topic") in topic_metric and not YES_NO.fullmatch(message):
        measurements = current_observations(session, crew_id, topic_metric[memory["topic"]])
    else:
        measurements = []
    answer, citations, engine = respond(
        [item["content"] for item in history if item["role"] == "user"] + [message], measurements,
        calculation.model_dump(mode="json"), request.app.state.chat_model,
        history + [{"role": "user", "content": message, "id": user_turn.id}],
        memory=memory, request_id=request_id,
    )
    diagnostics = getattr(request.app.state, "diagnostics", None)
    if diagnostics is not None:
        if engine.startswith("local_model_error:"):
            diagnostics.error(
                "chat_model_failed",
                extra={"request_id": request_id,
                       "code": getattr(request.app.state.chat_model, "last_validation_error", None) or "unavailable"},
            )
        elif engine.startswith("local_model:"):
            diagnostics.info("chat_model_completed", extra={"request_id": request_id})
    assistant_turn = ChatMessage(
        crew_member_id=crew_id, request_id=request_id, role="assistant", body=answer,
        source_report_id=user_turn.source_report_id,
        analysis_result_id=str(calculation.id), citations_json=json.dumps(citations), engine=engine,
    )
    session.add(assistant_turn)
    session.flush()
    if not engine.startswith("local_model_error:"):
        memory = delivered(memory, assistant_turn.id, answer)
        if memory.get("medical_history") and user_turn.source_report_id:
            memory["medical_history"][-1]["assessment"] = answer
            memory["medical_history"][-1]["citations"] = citations
        session.merge(ChatMemory(crew_member_id=crew_id, content_json=json.dumps(memory, ensure_ascii=False)))
    audit(session, "chat.assistant_created", "chat_message", assistant_turn.id, crew_id)
    session.commit()
    return {"crew_member_id": crew_id, "request_id": request_id, "messages": [chat_record(user_turn), chat_record(assistant_turn)],
            "analysis": calculation.model_dump(mode="json")}


@router.get("/baselines/{crew_id}", response_model=BaselineResponse, tags=["forecasting"])
def get_baseline(crew_id: UUID, session: Session = Depends(get_session)) -> BaselineResponse:
    crew = get_crew(session, crew_id)
    observations = current_observations(session, crew.id)
    metric_groups: dict[str, list[Observation]] = {}
    for observation in observations:
        metric_groups.setdefault(observation.metric, []).append(observation)
    metrics: list[BaselineMetricRead] = []
    for metric, group in sorted(metric_groups.items()):
        profile = baseline_profile(group)
        series = scalar_series(group)
        metrics.append(
            BaselineMetricRead(
                metric=metric,
                unit=series[-1].unit if series and len({item.unit for item in series}) == 1 else None,
                count=int(profile["count"]),
                median=profile["median"],
                mad=profile["mad"],
                interpretation="Descriptive personal statistical profile; it is not a validated physiological baseline.",
            )
        )
    return BaselineResponse(
        crew_member_id=crew_id,
        metrics=metrics,
        limitation="Values are descriptive only and do not establish clinical reference ranges or readiness.",
    )


@router.post("/forecasts/run", response_model=list[ForecastRead], status_code=status.HTTP_201_CREATED, tags=["forecasting"])
def run_forecast(payload: ForecastRunRequest, session: Session = Depends(get_session)) -> list[ForecastRead]:
    crew = get_crew(session, payload.crew_member_id)
    plan = forecast_series(current_observations(session, crew.id, payload.metric.value))
    forecasts: list[Forecast] = []
    for horizon in HORIZONS:
        prediction = plan.predictions.get(horizon)
        forecasts.append(
            Forecast(
                crew_member_id=crew.id,
                metric=payload.metric.value,
                horizon_hours=horizon,
                status=plan.horizon_status[horizon],
                method=plan.horizon_methods[horizon],
                unit=plan.unit,
                predicted_value=prediction,
                interval_low=plan.horizon_interval_low[horizon],
                interval_high=plan.horizon_interval_high[horizon],
                training_count=plan.training_count,
                evaluation_mae=plan.horizon_mae[horizon],
                interval_coverage=plan.horizon_interval_coverage[horizon],
                input_ids_json=json.dumps(plan.input_ids, separators=(",", ":")),
                insufficiency_reason=plan.horizon_reasons[horizon],
            )
        )
    session.add_all(forecasts)
    session.flush()
    audit(session, "forecast.completed", "forecast", forecasts[0].id, crew.id)
    session.commit()
    for forecast in forecasts:
        session.refresh(forecast)
    return [forecast_response(forecast).model_copy(update={
        "history_start_at": plan.history_start_at,
        "history_end_at": plan.history_end_at,
        "excluded_count": plan.excluded_count,
        "synthetic_count": plan.synthetic_count,
        "evaluation_count": plan.horizon_evaluation_count[forecast.horizon_hours],
        "baseline_mae": plan.horizon_baseline_mae[forecast.horizon_hours],
        "recent_values": plan.recent_values,
        "selection_mae": plan.horizon_selection_errors.get(forecast.horizon_hours, {}),
    }) for forecast in forecasts]

@router.post("/psychological-assessments", response_model=PsychologicalRead, status_code=201, tags=["psychology"])
def create_psychological(payload: PsychologicalCreate, request: Request, session: Session = Depends(get_session)) -> PsychologicalAssessment:
    require_automated_ingestion(request)
    crew = get_crew(session, payload.crew_member_id); reject_archived_crew(crew); get_source(session, payload.source_id)
    observed_at, _ = utc_storage(payload.observed_at)
    item = PsychologicalAssessment(crew_member_id=crew.id, source_id=str(payload.source_id), instrument=payload.instrument, mood=payload.mood, stress=payload.stress, fatigue=payload.fatigue, observed_at=observed_at, synthetic=payload.synthetic)
    session.add(item); session.flush(); audit(session, "psychological_assessment.created", "psychological_assessment", item.id, crew.id); session.commit(); session.refresh(item); return item

@router.get("/psychological-assessments", response_model=list[PsychologicalRead], tags=["psychology"])
def list_psychological(crew_member_id: UUID, session: Session = Depends(get_session)) -> list[PsychologicalAssessment]:
    return list(session.scalars(select(PsychologicalAssessment).where(PsychologicalAssessment.crew_member_id == str(crew_member_id)).order_by(PsychologicalAssessment.observed_at.desc())))

@router.post("/environmental-measurements", response_model=EnvironmentalRead, status_code=201, tags=["environment"])
def create_environment(payload: EnvironmentalCreate, request: Request, session: Session = Depends(get_session)) -> EnvironmentalMeasurement:
    require_automated_ingestion(request)
    get_source(session, payload.source_id); observed_at, _ = utc_storage(payload.observed_at)
    if payload.crew_member_id is not None:
        get_crew(session, payload.crew_member_id)
    item = EnvironmentalMeasurement(source_id=str(payload.source_id), crew_member_id=str(payload.crew_member_id) if payload.crew_member_id else None, metric=payload.metric, value=payload.value, unit=payload.unit.strip(), observed_at=observed_at, synthetic=payload.synthetic)
    session.add(item); session.flush(); audit(session, "environmental_measurement.created", "environmental_measurement", item.id); session.commit(); session.refresh(item); return item

@router.get("/environmental-measurements", response_model=list[EnvironmentalRead], tags=["environment"])
def list_environment(crew_member_id: UUID | None = None, limit: int = Query(default=100, ge=1, le=200), session: Session = Depends(get_session)) -> list[EnvironmentalMeasurement]:
    statement = select(EnvironmentalMeasurement)
    if crew_member_id is not None:
        statement = statement.where(EnvironmentalMeasurement.crew_member_id == str(crew_member_id))
    return list(session.scalars(statement.order_by(EnvironmentalMeasurement.observed_at.desc()).limit(limit)))

@router.post("/what-if-scenarios", response_model=WhatIfRead, status_code=201, tags=["simulation"])
def create_what_if(payload: WhatIfCreate, session: Session = Depends(get_session)) -> WhatIfRead:
    crew = get_crew(session, payload.crew_member_id)
    result = {"comparison": "Assumptions recorded for transparent comparison.", "causal_validity": "not_established", "clinical_validity": "not_established"}
    item = WhatIfScenario(crew_member_id=crew.id, name=payload.name.strip(), assumptions_json=json.dumps(payload.assumptions, sort_keys=True), result_json=json.dumps(result))
    session.add(item); session.flush(); audit(session, "what_if.created", "what_if_scenario", item.id, crew.id); session.commit(); session.refresh(item); return what_if_response(item)

@router.get("/crew-summary", tags=["crew"])
def crew_summary(session: Session = Depends(get_session)) -> dict:
    members = list(session.scalars(select(CrewMember).where(CrewMember.archived_at.is_(None))))
    return {"fictional_demo_only": True, "crew_count": len(members), "members": [{"crew_member_id": item.id, "display_name": item.display_name, "current_observation_count": len(current_observations(session, item.id))} for item in members], "limitation": "This aggregate does not provide health, mission-readiness, or fitness-for-duty conclusions."}

@router.get("/mission-readiness/{crew_id}", tags=["crew"])
def mission_readiness(crew_id: UUID, session: Session = Depends(get_session)) -> dict:
    crew = get_crew(session, crew_id)
    observations = current_observations(session, crew.id)
    reports = list(session.scalars(select(SymptomReport).where(
        SymptomReport.crew_member_id == crew.id,
        SymptomReport.withdrawn_at.is_(None),
        SymptomReport.superseded_by_id.is_(None),
    ).order_by(SymptomReport.observed_at, SymptomReport.id)))
    symptom_reports = [{"id": item.id, "description": item.description, "observed_at": item.observed_at.isoformat() + "Z"} for item in reports]
    environment = list(session.scalars(select(EnvironmentalMeasurement).where(
        EnvironmentalMeasurement.crew_member_id == crew.id
    )))
    environment_records = [{"id": item.id, "metric": item.metric, "value": item.value, "unit": item.unit} for item in environment]
    return assess_mission_readiness(crew, observations, symptom_reports, environment_records)

@router.post("/emergency-handoffs", response_model=HandoffRead, status_code=201, tags=["handoff"])
def create_handoff(payload: HandoffCreate, session: Session = Depends(get_session)) -> EmergencyHandoff:
    crew = get_crew(session, payload.crew_member_id)
    item = EmergencyHandoff(crew_member_id=crew.id, reason=payload.reason.strip())
    session.add(item); session.flush(); audit(session, "emergency_handoff.operator_declared", "emergency_handoff", item.id, crew.id); session.commit(); session.refresh(item); return item

@router.post("/emergency-handoffs/{handoff_id}/acknowledge", response_model=HandoffRead, tags=["handoff"])
def acknowledge_handoff(handoff_id: UUID, session: Session = Depends(get_session)) -> EmergencyHandoff:
    item = session.get(EmergencyHandoff, str(handoff_id))
    if item is None: raise not_found("Emergency handoff", handoff_id)
    if item.acknowledged_at is None:
        item.acknowledged_at = utc_now_naive(); item.status = "acknowledged"; audit(session, "emergency_handoff.acknowledged", "emergency_handoff", item.id); session.commit(); session.refresh(item)
    return item

@router.post("/sync/events", response_model=SyncEventRead, status_code=201, tags=["sync"])
def enqueue_sync_event(payload: SyncEventCreate, session: Session = Depends(get_session)) -> SyncEvent:
    existing = session.scalar(select(SyncEvent).where(SyncEvent.idempotency_key == payload.idempotency_key))
    if existing is not None: return existing
    encoded = json.dumps(payload.payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    item = SyncEvent(idempotency_key=payload.idempotency_key, event_type=payload.event_type, payload_sha256=hashlib.sha256(encoded).hexdigest())
    session.add(item); session.flush(); audit(session, "sync_event.queued", "sync_event", item.id); session.commit(); session.refresh(item); return item

@router.post("/sync/simulator/deliver", response_model=list[SyncEventRead], tags=["sync"])
def deliver_sync_events(session: Session = Depends(get_session)) -> list[SyncEvent]:
    events = list(session.scalars(select(SyncEvent).where(SyncEvent.status == "queued").order_by(SyncEvent.created_at)))
    for item in events:
        item.attempts += 1; item.status = "acknowledged"; item.acknowledged_at = utc_now_naive(); audit(session, "sync_event.acknowledged", "sync_event", item.id)
    session.commit()
    for item in events: session.refresh(item)
    return events
