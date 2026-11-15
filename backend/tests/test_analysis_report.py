"""Structured report preserves per-parameter uncertainty and input provenance."""

import asyncio
from pathlib import Path

import httpx
import pytest

from app.db import sqlite_url, upgrade_database
from app.main import create_app


@pytest.fixture
def app(tmp_path: Path):
    database_url = sqlite_url(tmp_path / "report.sqlite3")
    upgrade_database(database_url)
    application = create_app(database_url=database_url, automated_ingestion_enabled=True)
    yield application
    application.state.database.dispose()


def request(app, method: str, path: str, payload: dict | None = None) -> httpx.Response:
    async def send() -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await client.request(method, path, json=payload)
    return asyncio.run(send())


def setup(app) -> tuple[str, str]:
    crew = request(app, "POST", "/api/v1/crew", {"display_name": "Fictional Report Crew"})
    source = request(app, "POST", "/api/v1/data-sources", {
        "title": "Synthetic report source", "source_type": "synthetic"
    })
    assert crew.status_code == source.status_code == 201
    return crew.json()["id"], source.json()["id"]


def add(app, crew_id: str, source_id: str, metric: str, amount: float, unit: str, minute: int,
        flags: list[str] | None = None) -> None:
    response = request(app, "POST", "/api/v1/observations", {
        "crew_member_id": crew_id, "source_id": source_id, "metric": metric,
        "value": {"kind": "scalar", "amount": amount}, "unit": unit,
        "observed_at": f"2030-01-01T00:{minute:02d}:00+00:00",
        "synthetic": True, "quality_flags": flags or [],
    })
    assert response.status_code == 201, response.text


def run(app, crew_id: str) -> dict:
    response = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert response.status_code in {200, 201}, response.text
    return response.json()


def test_per_parameter_results_preserve_conditional_reference_and_missingness(app) -> None:
    crew_id, source_id = setup(app)
    add(app, crew_id, source_id, "heart_rate", 72, "bpm", 0)
    add(app, crew_id, source_id, "spo2", 90, "%", 1)
    add(app, crew_id, source_id, "body_temperature", 36.4, "°C", 2)
    result = run(app, crew_id)
    items = {item["metric"]: item for item in result["parameter_assessments"]}
    assert items["heart_rate"]["status"] == "within_available_reference"
    assert items["heart_rate"]["reference"]["applicability"] == "unverified"
    assert items["heart_rate"]["synthetic"] is True
    assert items["heart_rate"]["availability_class"] == "synthetic"
    assert items["heart_rate"]["personal_series"]["approved"] is False
    assert items["heart_rate"]["freshness_status"] == "not_assessed_no_schedule"
    assert items["spo2"]["status"] == "outside_available_reference"
    assert items["spo2"]["reference"]["source_url"].startswith("https://www.fda.gov/")
    assert items["body_temperature"]["status"] == "within_available_reference"
    assert "38" in items["body_temperature"]["explanation"]
    report = result["integrated_report"]
    assert "blood_pressure" in report["coverage"]["not_recorded_metrics"]
    assert report["observed_facts"] == []  # Parameter rows already contain the measurements.
    assert not any(item.get("status") == "reference_comparison" for item in report["deterministic_findings"])
    assert report["scenario_comparison"]["status"] == "unsupported_without_evaluated_causal_model"
    assert report["provenance"]["input_ids"] == result["input_ids"]
    fetched = request(app, "GET", f"/api/v1/analysis/{result['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["parameter_assessments"] == result["parameter_assessments"]


def test_declared_stale_conflict_and_structural_invalidity_abstain(app) -> None:
    crew_id, source_id = setup(app)
    add(app, crew_id, source_id, "heart_rate", 72, "bpm", 0)
    add(app, crew_id, source_id, "heart_rate", 73, "beats/min", 1)
    add(app, crew_id, source_id, "spo2", 98, "%", 2, ["stale"])
    add(app, crew_id, source_id, "respiratory_rate", -1, "breaths/min", 3)
    result = run(app, crew_id)
    items = {item["metric"]: item for item in result["parameter_assessments"]}
    assert items["heart_rate"]["status"] == "conflicting"
    assert items["heart_rate"]["reference"]["status"] == "not_assessed"
    assert items["spo2"]["status"] == "stale"
    assert items["spo2"]["reference"]["status"] == "not_assessed"
    assert items["respiratory_rate"]["status"] == "invalid"
    assert items["respiratory_rate"]["reference"]["status"] == "not_assessed"
    assert not any(item.get("rule_id") == "reference_comparison" for item in result["findings"])


def test_lab_records_are_not_active_and_context_changes_invalidate_cache(app) -> None:
    crew_id, source_id = setup(app)
    add(app, crew_id, source_id, "lab_value", 1, "unit", 0)
    first = run(app, crew_id)
    assert first["parameter_assessments"] == []
    assert first["facts"][0]["value"] == 0
    symptom = request(app, "POST", "/api/v1/symptoms", {
        "crew_member_id": crew_id, "source_id": source_id,
        "description": "Fictional test complaint", "observed_at": "2030-01-01T00:01:00+00:00",
        "synthetic": True,
    })
    assert symptom.status_code == 201, symptom.text
    second = run(app, crew_id)
    assert second["id"] != first["id"]
    assert second["integrated_report"]["coverage"]["symptom_report_count"] == 1
    assert second["integrated_report"]["complaint_review"][0]["description"] == "Fictional test complaint"
    assert second["integrated_report"]["complaint_review"][0]["synthetic"] is True
    environment = request(app, "POST", "/api/v1/environmental-measurements", {
        "source_id": source_id, "crew_member_id": crew_id, "metric": "co2", "value": 600, "unit": "ppm",
        "observed_at": "2030-01-01T00:02:00+00:00", "synthetic": True,
    })
    assert environment.status_code == 201, environment.text
    third = run(app, crew_id)
    assert third["id"] != second["id"]
    assert third["integrated_report"]["mission_environment_context"]["status"] == "profile_environment_only"
    assert third["integrated_report"]["possible_explanations"] == []


def test_russian_complaint_numbers_and_profile_mission_change_are_used(app) -> None:
    crew_id, _ = setup(app)
    mission = request(app, "PATCH", f"/api/v1/crew/{crew_id}/mission", {
        "mission_location": "iss", "mission_phase": "orbit", "habitat": "учебный модуль",
    })
    assert mission.status_code == 200, mission.text
    complaint = request(app, "POST", "/api/v1/manual/complaints", {
        "crew_member_id": crew_id,
        "description": "Болит голова, давление 150/95, пульс 90.",
        "observed_at": "2030-01-01T00:00:00+00:00",
    })
    assert complaint.status_code == 201, complaint.text
    assert {item["metric"] for item in complaint.json()["parsed_measurements"]} == {"blood_pressure", "heart_rate"}
    assert complaint.json()["recognized_symptom_codes"] == ["headache"]
    first = run(app, crew_id)
    assert first["integrated_report"]["coverage"]["observation_count"] == 2
    pressure = next(item for item in first["parameter_assessments"] if item["metric"] == "blood_pressure")
    assert pressure["reference"]["status"] == "bp_stage2_range"
    assert any(item.get("kind") == "repeat_blood_pressure" for item in first["integrated_report"]["next_steps"])
    assert first["integrated_report"]["mission_environment_context"]["location"] == "iss"
    assert first["integrated_report"]["complaint_review"][0]["description"].startswith("Болит голова")
    assert first["integrated_report"]["complaint_review"][0]["source_type"] == "manual"
    mission = request(app, "PATCH", f"/api/v1/crew/{crew_id}/mission", {
        "mission_location": "moon", "mission_phase": "surface", "habitat": "новый учебный модуль",
    })
    assert mission.status_code == 200, mission.text
    second = run(app, crew_id)
    assert second["id"] != first["id"]
    assert second["integrated_report"]["mission_environment_context"]["location"] == "moon"
