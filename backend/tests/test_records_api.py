import asyncio
import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import inspect

from app.db import sqlite_url, upgrade_database
from app.assistant import LocalAssistant
from app.main import create_app


@pytest.fixture
def app(tmp_path: Path):
    database_url = sqlite_url(tmp_path / "astra-test.sqlite3")
    upgrade_database(database_url)
    application = create_app(database_url=database_url, automated_ingestion_enabled=True)
    yield application
    application.state.database.dispose()


def request(app, method: str, path: str, payload: dict | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


def create_crew_and_source(app) -> tuple[str, str]:
    crew = request(app, "POST", "/api/v1/crew", {"display_name": "Astra Demo One"})
    source = request(
        app,
        "POST",
        "/api/v1/data-sources",
        {"title": "Manual demo entry", "source_type": "manual", "version": "stage-2"},
    )
    assert crew.status_code == 201
    assert source.status_code == 201
    return crew.json()["id"], source.json()["id"]


def test_manual_mode_assigns_provenance_and_blocks_legacy_ingestion(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "manual-mode.sqlite3")
    upgrade_database(database_url)
    application = create_app(database_url=database_url, automated_ingestion_enabled=False)
    try:
        crew = request(application, "POST", "/api/v1/crew", {"display_name": "Astra Demo One"})
        assert crew.status_code == 201
        crew_id = crew.json()["id"]
        created = request(application, "POST", "/api/v1/manual/observations", {
            "crew_member_id": crew_id,
            "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 72},
            "unit": "bpm",
            "observed_at": "2026-11-06T14:30:00+03:00",
        })
        assert created.status_code == 201
        assert created.json()["synthetic"] is False
        assert created.json()["quality_flags"] == []
        sources = request(application, "GET", "/api/v1/data-sources")
        assert len(sources.json()) == 1
        assert sources.json()[0]["id"] == created.json()["source_id"]
        assert sources.json()[0]["source_type"] == "manual"
        assert request(application, "POST", "/api/v1/data-sources", {
            "title": "Import", "source_type": "import", "version": "1",
        }).status_code == 403
        assert request(application, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 80}, "unit": "bpm",
            "observed_at": "2026-11-06T14:31:00+03:00",
            "source_id": sources.json()[0]["id"], "synthetic": True,
        }).status_code == 403
        assert request(application, "PATCH", f"/api/v1/observations/{created.json()['id']}", {
            "metric": "heart_rate", "value": {"kind": "scalar", "amount": 73},
            "unit": "bpm", "observed_at": "2026-11-06T14:32:00+03:00",
            "source_id": sources.json()[0]["id"], "synthetic": True,
        }).status_code == 403
        assert request(application, "POST", "/api/v1/synthetic-scenarios/runs", {
            "crew_member_id": crew_id, "scenario": "normal", "seed": 42,
        }).status_code == 403
        analysis = request(application, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
        assert analysis.json()["facts"][0]["value"] == 1
        assert analysis.json()["findings"] == []
    finally:
        application.state.database.dispose()


def test_provenance_flags_do_not_create_quality_alerts(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    for number in range(8):
        created = request(app, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 70 + number}, "unit": "bpm",
            "observed_at": f"2030-01-{number + 1:02d}T00:00:00+00:00",
            "source_id": source_id, "synthetic": True,
            "quality_flags": ["synthetic_ui_entry"],
        })
        assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert analysis.json()["facts"][0]["value"] == 8
    assert analysis.json()["findings"] == []
    assert request(app, "GET", f"/api/v1/alerts?crew_member_id={crew_id}").json() == []


def test_single_measurements_produce_metric_review_without_claiming_normality(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    samples = [
        ("heart_rate", 120, "bpm"),
        ("spo2", 10, "%"),
        ("body_temperature", 36.4, "°C"),
        ("respiratory_rate", 200, "breaths/min"),
        ("sleep_duration", 8, "h"),
        ("sleep_quality", 3, "score"),
        ("activity", 400, "steps"),
        ("exertion_fatigue", 9, "score"),
    ]
    for minute, (metric, amount, unit) in enumerate(samples):
        created = request(app, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "metric": metric,
            "value": {"kind": "scalar", "amount": amount}, "unit": unit,
            "observed_at": f"2030-01-01T00:{minute:02d}:00+00:00",
            "source_id": source_id, "synthetic": True,
            "quality_flags": ["synthetic_ui_entry"],
        })
        assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert analysis.status_code == 201
    facts = analysis.json()["facts"]
    snapshots = {item["metric"]: item for item in facts if item["kind"] == "metric_snapshot"}
    assert len(snapshots) == 8
    assert snapshots["spo2"]["latest_value"] == {"kind": "scalar", "amount": 10.0}
    assert snapshots["respiratory_rate"]["latest_value"] == {"kind": "scalar", "amount": 200.0}
    assert all(item["comparison_status"] == "single_point" for item in snapshots.values())
    coverage = next(item for item in facts if item["kind"] == "series_coverage")
    assert coverage["metrics_with_repeat"] == 0
    assert coverage["metrics_without_repeat"] == 8
    assert any(item["kind"] == "personal_history" for item in analysis.json()["unknowns"])
    assert {item["rule_id"] for item in analysis.json()["findings"]} == {
        "reference_comparison", "coincident_oxygen_breathing"
    }
    references = {item["metric"]: item for item in facts if item["kind"] == "reference_review"}
    assert references["heart_rate"]["status"] == "above_reference"
    assert references["spo2"]["status"] == "below_reference"
    assert references["respiratory_rate"]["status"] == "above_reference"
    assert references["sleep_duration"]["status"] == "meets_minimum"
    assert references["sleep_quality"]["status"] == "not_assessed"
    assert analysis.json()["guidance"]
    assert analysis.json()["hypotheses"][0]["kind"] == "possible_low_oxygen"
    repeated = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert repeated.status_code == 200
    assert repeated.json()["id"] == analysis.json()["id"]


def test_mixed_units_are_not_compared_as_one_series(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    for minute, unit in enumerate(("°C", "°F")):
        created = request(app, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "metric": "body_temperature",
            "value": {"kind": "scalar", "amount": 36 + minute}, "unit": unit,
            "observed_at": f"2030-01-01T00:{minute:02d}:00+00:00",
            "source_id": source_id, "synthetic": True, "quality_flags": [],
        })
        assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id}).json()
    snapshot = next(item for item in analysis["facts"] if item["kind"] == "metric_snapshot")
    assert snapshot["comparison_status"] == "mixed_units"
    assert "delta_from_previous" not in snapshot
    assert any(item["rule_id"] == "unit_mismatch" for item in analysis["findings"])


def test_reference_check_requires_expected_unit(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    created = request(app, "POST", "/api/v1/observations", {
        "crew_member_id": crew_id, "metric": "spo2",
        "value": {"kind": "scalar", "amount": 10}, "unit": "bpm",
        "observed_at": "2030-01-01T00:00:00+00:00",
        "source_id": source_id, "synthetic": True, "quality_flags": [],
    })
    assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id}).json()
    review = next(item for item in analysis["facts"] if item["kind"] == "reference_review")
    assert review["status"] == "not_assessed"
    assert review["reason"] == "unit_not_comparable"
    assert analysis["findings"] == []


def test_coincident_readings_require_close_timestamps(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    for metric, amount, unit, observed_at in (
        ("spo2", 10, "%", "2030-01-01T00:00:00+00:00"),
        ("respiratory_rate", 200, "breaths/min", "2030-01-02T00:00:00+00:00"),
    ):
        created = request(app, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "metric": metric,
            "value": {"kind": "scalar", "amount": amount}, "unit": unit,
            "observed_at": observed_at, "source_id": source_id,
            "synthetic": True, "quality_flags": [],
        })
        assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id}).json()
    assert "coincident_oxygen_breathing" not in {item["rule_id"] for item in analysis["findings"]}


def test_migration_creates_required_tables(app) -> None:
    tables = set(inspect(app.state.database.engine).get_table_names())
    assert {
        "alembic_version",
        "crew_members",
        "data_sources",
        "observations",
        "symptom_reports",
        "audit_events",
        "ingestion_records",
        "scenario_runs",
        "analysis_results",
        "alerts",
        "forecasts",
        "psychological_assessments",
        "environmental_measurements",
        "what_if_scenarios",
        "emergency_handoffs",
        "sync_events",
    } <= tables


def test_fictional_record_lifecycle_preserves_revision_history(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    observation_payload = {
        "crew_member_id": crew_id,
        "metric": "heart_rate",
        "value": {"kind": "scalar", "amount": 72},
        "unit": "bpm",
        "observed_at": "2026-11-06T14:30:00+03:00",
        "source_id": source_id,
        "synthetic": True,
        "quality_flags": ["demo"],
    }
    created = request(app, "POST", "/api/v1/observations", observation_payload)
    assert created.status_code == 201
    assert created.json()["value"] == {"kind": "scalar", "amount": 72.0}
    assert created.json()["observed_at"] == "2026-11-06T11:30:00Z"
    observation_id = created.json()["id"]

    revision_payload = {
        **{key: value for key, value in observation_payload.items() if key != "crew_member_id"},
        "value": {"kind": "scalar", "amount": 74},
    }
    revised = request(app, "PATCH", f"/api/v1/observations/{observation_id}", revision_payload)
    assert revised.status_code == 201
    assert revised.json()["supersedes_id"] == observation_id
    revised_id = revised.json()["id"]

    original = request(app, "GET", f"/api/v1/observations/{observation_id}")
    assert original.status_code == 200
    assert original.json()["superseded_by_id"] == revised_id

    withdrawn = request(
        app, "DELETE", f"/api/v1/observations/{revised_id}", {"reason": "Synthetic entry replaced."}
    )
    assert withdrawn.status_code == 204
    hidden = request(app, "GET", "/api/v1/observations")
    assert hidden.json() == [original.json()]
    assert request(app, "GET", "/api/v1/observations?current_only=true").json() == []
    full_history = request(app, "GET", "/api/v1/observations?include_withdrawn=true")
    assert len(full_history.json()) == 2
    audit = request(app, "GET", "/api/v1/audit-events")
    assert {event["action"] for event in audit.json()} >= {
        "crew.created",
        "data_source.created",
        "observation.created",
        "observation.revised",
        "observation.withdrawn",
    }


def test_blood_pressure_and_symptom_contracts_reject_invalid_inputs(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    invalid_time = request(
        app,
        "POST",
        "/api/v1/observations",
        {
            "crew_member_id": crew_id,
            "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 72},
            "unit": "bpm",
            "observed_at": "2026-11-06T14:30:00",
            "source_id": source_id,
            "synthetic": True,
        },
    )
    assert invalid_time.status_code == 422

    invalid_shape = request(
        app,
        "POST",
        "/api/v1/observations",
        {
            "crew_member_id": crew_id,
            "metric": "blood_pressure",
            "value": {"kind": "scalar", "amount": 72},
            "unit": "mmHg",
            "observed_at": "2026-11-06T14:30:00+00:00",
            "source_id": source_id,
            "synthetic": True,
        },
    )
    assert invalid_shape.status_code == 422

    pressure = request(
        app,
        "POST",
        "/api/v1/observations",
        {
            "crew_member_id": crew_id,
            "metric": "blood_pressure",
            "value": {"kind": "blood_pressure", "systolic": 120, "diastolic": 80},
            "unit": "mmHg",
            "observed_at": "2026-11-06T14:30:00+00:00",
            "source_id": source_id,
            "synthetic": True,
        },
    )
    assert pressure.status_code == 201

    symptom = request(
        app,
        "POST",
        "/api/v1/symptoms",
        {
            "crew_member_id": crew_id,
            "description": "Synthetic free-text demo report.",
            "observed_at": "2026-11-06T14:30:00+00:00",
            "source_id": source_id,
            "synthetic": True,
        },
    )
    assert symptom.status_code == 201
    assert symptom.json()["description"] == "Synthetic free-text demo report."


def test_archived_profile_rejects_new_records(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    archived = request(app, "DELETE", f"/api/v1/crew/{crew_id}")
    assert archived.status_code == 204
    rejected = request(
        app,
        "POST",
        "/api/v1/observations",
        {
            "crew_member_id": crew_id,
            "metric": "spo2",
            "value": {"kind": "scalar", "amount": 98},
            "unit": "%",
            "observed_at": "2026-11-06T14:30:00+00:00",
            "source_id": source_id,
            "synthetic": True,
        },
    )
    assert rejected.status_code == 409


def test_seeded_scenarios_are_reproducible_and_urgent_is_explicit(app) -> None:
    crew_id, _ = create_crew_and_source(app)
    payload = {
        "crew_member_id": crew_id,
        "scenario": "gradual_change",
        "seed": 42,
        "start_at": "2030-01-01T00:00:00+00:00",
    }
    first = request(app, "POST", "/api/v1/synthetic-scenarios/runs", payload)
    second = request(app, "POST", "/api/v1/synthetic-scenarios/runs", payload)
    assert first.status_code == second.status_code == 201
    assert first.json()["event_fingerprint"] == second.json()["event_fingerprint"]
    assert len(first.json()["observation_ids"]) == 4
    assert first.json()["declared_urgent"] is False

    urgent = request(
        app,
        "POST",
        "/api/v1/synthetic-scenarios/runs",
        {**payload, "scenario": "operator_declared_urgent"},
    )
    assert urgent.status_code == 201
    assert urgent.json()["declared_urgent"] is True
    observation = request(app, "GET", f"/api/v1/observations/{urgent.json()['observation_ids'][0]}")
    assert "operator_declared_urgent_demo" in observation.json()["quality_flags"]


def test_csv_import_accepts_valid_rows_and_quarantines_invalid_rows_without_raw_data(app) -> None:
    crew_id, _ = create_crew_and_source(app)
    csv_content = "\n".join(
        [
            "metric,value_kind,amount,systolic,diastolic,unit,observed_at,synthetic,quality_flags",
            "heart_rate,scalar,71,,,bpm,2030-01-01T00:00:00+00:00,true,imported|synthetic",
            "blood_pressure,scalar,broken,,,mmHg,2030-01-01T01:00:00+00:00,true,",
        ]
    )
    imported = request(
        app,
        "POST",
        "/api/v1/imports/csv",
        {
            "crew_member_id": crew_id,
            "filename": "demo.csv",
            "content": csv_content,
            "source_title": "Synthetic CSV import",
            "source_version": "v1",
        },
    )
    assert imported.status_code == 201
    assert imported.json()["accepted_observations"] == 1
    assert imported.json()["quarantined_rows"] == 1
    source_id = imported.json()["source"]["id"]
    records = request(app, "GET", f"/api/v1/ingestion-records?source_id={source_id}")
    assert records.status_code == 200
    assert records.json()[0]["status"] == "quarantined"
    assert records.json()[0]["reason"] == "Row failed structural validation."
    assert "broken" not in str(records.json()[0])


def test_deterministic_analysis_separates_findings_and_unknowns(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    created = request(
        app,
        "POST",
        "/api/v1/observations",
        {
            "crew_member_id": crew_id,
            "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 72},
            "unit": "bpm",
            "observed_at": "2030-01-01T00:00:00+00:00",
            "source_id": source_id,
            "synthetic": True,
            "quality_flags": ["demonstration_only", "suspect"],
        },
    )
    assert created.status_code == 201
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert analysis.status_code == 201
    assert analysis.json()["guidance"] == []
    assert analysis.json()["hypotheses"] == []
    assert analysis.json()["findings"][0]["clinical_significance"] == "not_established"
    assert "not validated mission-specific limits" in analysis.json()["unknowns"][0]["statement"]
    alerts = request(app, "GET", f"/api/v1/alerts?crew_member_id={crew_id}")
    assert alerts.status_code == 200
    assert alerts.json()[0]["rule_id"] == "quality_flags_present"

    app.state.local_assistant = LocalAssistant(base_url="http://127.0.0.1:1", model="missing")
    answer = request(
        app,
        "POST",
        "/api/v1/assistant/explain",
        {"crew_member_id": crew_id, "analysis_result_id": analysis.json()["id"], "question": "Diagnose this."},
    )
    assert answer.status_code == 200
    assert answer.json()["status"] == "fallback"
    assert "72.0 bpm" in answer.json()["answer"]
    assert answer.json()["citations"][0] == "ASTRA Evidence Rules, §1–§3"


def test_time_aware_forecast_refuses_then_returns_three_horizons_with_history(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    insufficient = request(app, "POST", "/api/v1/forecasts/run", {"crew_member_id": crew_id, "metric": "heart_rate"})
    assert insufficient.status_code == 201
    assert {item["status"] for item in insufficient.json()} == {"insufficient"}

    for day in range(8):
        response = request(
            app,
            "POST",
            "/api/v1/observations",
            {
                "crew_member_id": crew_id,
                "metric": "heart_rate",
                "value": {"kind": "scalar", "amount": 60 + day},
                "unit": "bpm",
                "observed_at": f"2030-01-{day + 1:02d}T00:00:00+00:00",
                "source_id": source_id,
                "synthetic": True,
                "quality_flags": [],
            },
        )
        assert response.status_code == 201
    baseline = request(app, "GET", f"/api/v1/baselines/{crew_id}")
    assert baseline.status_code == 200
    assert baseline.json()["metrics"][0]["count"] == 8

    forecast = request(app, "POST", "/api/v1/forecasts/run", {"crew_member_id": crew_id, "metric": "heart_rate"})
    assert forecast.status_code == 201
    assert [item["horizon_hours"] for item in forecast.json()] == [24, 72, 168]
    by_horizon = {item["horizon_hours"]: item for item in forecast.json()}
    assert by_horizon[24]["status"] == "available"
    assert by_horizon[24]["evaluation_mae"] is not None
    assert by_horizon[72]["status"] == "insufficient"
    assert by_horizon[168]["status"] == "insufficient"
    assert by_horizon[168]["predicted_value"] is None
    assert "7 days" in by_horizon[168]["insufficiency_reason"]


def test_local_assistant_rejects_an_unsourced_model_response(monkeypatch) -> None:
    import app.assistant as assistant_module

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return b'{"message":{"content":"This is an unsupported explanation."}}'

    monkeypatch.setattr(assistant_module, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    status, answer = LocalAssistant(enable_experimental=True).explain({"findings": []}, None)
    assert status == "insufficient_evidence"
    assert "Not enough" in answer


def test_local_assistant_accepts_only_required_structured_response(monkeypatch) -> None:
    import app.assistant as assistant_module

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *_): return False
        def read(self): return json.dumps({"message": {"content": json.dumps({"summary": "There are no comparable measurements for the overview yet.", "citation": "ASTRA Evidence Rules, §1–§3", "not_a_diagnosis": True}, ensure_ascii=False)}}, ensure_ascii=False).encode("utf-8")

    monkeypatch.setattr(assistant_module, "urlopen", lambda *_args, **_kwargs: FakeResponse())
    status, answer = LocalAssistant(enable_experimental=True).explain({"findings": []}, None)
    assert status == "available"
    assert answer == "There are no comparable measurements for the overview yet."


def test_p1_context_simulation_handoff_and_sync_are_local_and_auditable(app) -> None:
    crew_id, source_id = create_crew_and_source(app)
    psychological = request(app, "POST", "/api/v1/psychological-assessments", {"crew_member_id": crew_id, "source_id": source_id, "mood": 5, "stress": 4, "fatigue": 3, "observed_at": "2030-01-01T00:00:00+00:00", "synthetic": True})
    environment = request(app, "POST", "/api/v1/environmental-measurements", {"source_id": source_id, "metric": "co2", "value": 600, "unit": "ppm", "observed_at": "2030-01-01T00:00:00+00:00", "synthetic": True})
    scenario = request(app, "POST", "/api/v1/what-if-scenarios", {"crew_member_id": crew_id, "name": "Workload comparison", "assumptions": {"workload": "higher", "hours": 2}})
    assert psychological.status_code == environment.status_code == scenario.status_code == 201
    assert scenario.json()["result"]["causal_validity"] == "not_established"
    readiness = request(app, "GET", f"/api/v1/mission-readiness/{crew_id}")
    assert readiness.json()["status"] == "not_assessed"
    handoff = request(app, "POST", "/api/v1/emergency-handoffs", {"crew_member_id": crew_id, "reason": "Operator-declared synthetic drill."})
    assert handoff.status_code == 201
    acknowledged = request(app, "POST", f"/api/v1/emergency-handoffs/{handoff.json()['id']}/acknowledge")
    assert acknowledged.json()["status"] == "acknowledged"
    event_payload = {"idempotency_key": "demo-sync-event-001", "event_type": "demo.summary", "payload": {"crew": crew_id}}
    queued = request(app, "POST", "/api/v1/sync/events", event_payload)
    duplicate = request(app, "POST", "/api/v1/sync/events", event_payload)
    assert queued.json()["id"] == duplicate.json()["id"]
    delivered = request(app, "POST", "/api/v1/sync/simulator/deliver")
    assert delivered.status_code == 200
    assert delivered.json()[0]["status"] == "acknowledged"
    assert delivered.json()[0]["attempts"] == 1
