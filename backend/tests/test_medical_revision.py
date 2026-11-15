"""Acceptance checks for provenance, conditional wound guidance and local screening."""

import asyncio
from pathlib import Path

import httpx
import pytest

from app.db import sqlite_url, upgrade_database
from app.main import create_app
from app.complaint_parser import symptom_codes


@pytest.fixture
def app(tmp_path: Path):
    url = sqlite_url(tmp_path / "revision.sqlite3")
    upgrade_database(url)
    application = create_app(database_url=url, automated_ingestion_enabled=True)
    yield application
    application.state.database.dispose()


def request(app, method: str, path: str, data: dict | None = None) -> httpx.Response:
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=data)
    return asyncio.run(send())


def new_crew(app) -> str:
    response = request(app, "POST", "/api/v1/crew", {"display_name": "\u0423\u0447\u0435\u0431\u043d\u044b\u0439 \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438"})
    assert response.status_code == 201
    return response.json()["id"]


def add_manual_heart_rate(app, crew_id: str, value: float = 72) -> None:
    response = request(app, "POST", "/api/v1/manual/observations", {
        "crew_member_id": crew_id, "metric": "heart_rate", "value": {"kind": "scalar", "amount": value},
        "unit": "bpm", "observed_at": "2030-01-01T00:00:00+00:00",
    })
    assert response.status_code == 201, response.text


def test_elbow_report_preserves_provenance_and_conditional_steps(app) -> None:
    crew_id = new_crew(app)
    complaint = "\u041f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443 \u0432 \u0440\u0430\u0439\u043e\u043d\u0435 \u043b\u043e\u043a\u0442\u044f. \u0422\u0435\u0447\u0435\u0442 \u0442\u0435\u043c\u043d\u0430\u044f \u043a\u0440\u043e\u0432\u044c"
    created = request(app, "POST", "/api/v1/manual/complaints", {
        "crew_member_id": crew_id, "description": complaint, "observed_at": "2030-01-01T01:02:00+00:00",
    })
    assert created.status_code == 201, created.text
    assert created.json()["parsed_measurements"] == []
    analysis = request(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert analysis.status_code == 201, analysis.text
    report = analysis.json()["integrated_report"]
    review = report["complaint_review"][0]
    assert review["report_id"] == created.json()["symptom_report_id"]
    assert review["description"] == complaint
    assert review["observed_at"] == "2030-01-01T01:02:00Z"
    assert review["source_id"] and review["source_type"] == "manual"
    assert review["synthetic"] is False
    assert review["location"] == "elbow area on the arm"
    assert any("object" in question for question in review["unknowns"])
    assert "cannot be established" in review["interpretation"]
    assert report["diagnostic_candidates"] == []
    steps = [item for item in report["next_steps"] if item.get("report_id") == review["report_id"]]
    assert [item["order"] for item in steps] == list(range(1, 7))
    assert all(item.get("why") and item.get("condition") and item.get("escalation") and item.get("source_url", "").startswith("https://") for item in steps)
    assert "If there is no object in the wound" in steps[2]["statement"]
    assert "If an object is lodged" in steps[3]["statement"]
    assert "flight medic" in steps[-1]["statement"]
    assert "ambulance" not in str(steps).lower()
    assert report["scenario_comparison"]["status"] == "qualitative_conditional_not_individual_prediction"
    assert "external_bleeding" not in symptom_codes("\u041d\u0435 \u0442\u0435\u0447\u0435\u0442 \u0442\u0435\u043c\u043d\u0430\u044f \u043a\u0440\u043e\u0432\u044c")


def test_readiness_uses_explicit_criteria_and_unresolved_complaint(app) -> None:
    crew_id = new_crew(app)
    empty = request(app, "GET", f"/api/v1/mission-readiness/{crew_id}").json()
    assert empty["status"] == "not_assessed"
    assert empty["criteria_configured"] is True
    mission = request(app, "PATCH", f"/api/v1/crew/{crew_id}/mission", {
        "mission_location": "iss", "mission_phase": "orbit", "habitat": "\u0443\u0447\u0435\u0431\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c",
    })
    assert mission.status_code == 200
    add_manual_heart_rate(app, crew_id)
    clear = request(app, "GET", f"/api/v1/mission-readiness/{crew_id}").json()
    assert clear["status"] == "meets_configured_criteria"
    assert clear["required_human_follow_up"] is True
    assert any("criticality" in value.lower() for value in clear["missing_data"])
    request(app, "POST", "/api/v1/manual/complaints", {
        "crew_member_id": crew_id, "description": "\u041f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443 \u0432 \u0440\u0430\u0439\u043e\u043d\u0435 \u043b\u043e\u043a\u0442\u044f. \u0422\u0435\u0447\u0435\u0442 \u0442\u0435\u043c\u043d\u0430\u044f \u043a\u0440\u043e\u0432\u044c",
        "observed_at": "2030-01-01T01:02:00+00:00",
    })
    review = request(app, "GET", f"/api/v1/mission-readiness/{crew_id}").json()
    assert review["status"] == "conditional_review"
    bleeding = next(item for item in review["contributing_factors"] if item["criterion_id"] == "reported_bleeding")
    assert bleeding["met"] is False
    assert "\u041f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443" in bleeding["evidence"]
    assert "not medical clearance" in review["criteria_scope"].lower()


def test_forecast_has_independent_horizon_evaluation_and_russian_reasons(app) -> None:
    crew_id = new_crew(app)
    source = request(app, "POST", "/api/v1/data-sources", {"title": "\u0421\u0438\u043d\u0442\u0435\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0440\u044f\u0434", "source_type": "synthetic"}).json()["id"]
    for day in range(16):
        created = request(app, "POST", "/api/v1/observations", {
            "crew_member_id": crew_id, "source_id": source, "metric": "heart_rate",
            "value": {"kind": "scalar", "amount": 60 + day % 3}, "unit": "bpm",
            "observed_at": f"2030-01-{day + 1:02d}T00:00:00+00:00",
            "synthetic": True, "quality_flags": [],
        })
        assert created.status_code == 201, created.text
    forecast = request(app, "POST", "/api/v1/forecasts/run", {"crew_member_id": crew_id, "metric": "heart_rate"})
    assert forecast.status_code == 201, forecast.text
    rows = forecast.json()
    assert [row["horizon_hours"] for row in rows] == [24, 72, 168]
    assert all(row["status"] == "available" and row["evaluation_count"] >= 2 for row in rows)
    assert all(row["synthetic_count"] == 16 for row in rows)
    assert rows[0]["history_start_at"] == "2030-01-01T00:00:00Z"
    assert all(row["recent_values"] and row["selection_mae"] for row in rows)


def test_stale_last_value_prevents_clear_readiness(app) -> None:
    crew_id = new_crew(app)
    mission = request(app, "PATCH", f"/api/v1/crew/{crew_id}/mission", {
        "mission_location": "moon", "mission_phase": "surface", "habitat": "\u0443\u0447\u0435\u0431\u043d\u044b\u0439 \u043c\u043e\u0434\u0443\u043b\u044c",
    })
    assert mission.status_code == 200
    source = request(app, "POST", "/api/v1/data-sources", {"title": "\u0422\u0435\u0441\u0442\u043e\u0432\u043e\u0435 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u0435", "source_type": "synthetic"}).json()["id"]
    record = request(app, "POST", "/api/v1/observations", {
        "crew_member_id": crew_id, "source_id": source, "metric": "heart_rate",
        "value": {"kind": "scalar", "amount": 73}, "unit": "bpm",
        "observed_at": "2030-01-01T00:00:00+00:00", "synthetic": True,
        "quality_flags": ["stale"],
    })
    assert record.status_code == 201
    readiness = request(app, "GET", f"/api/v1/mission-readiness/{crew_id}").json()
    assert readiness["status"] == "conditional_review"
    quality = next(item for item in readiness["contributing_factors"] if item["criterion_id"] == "input_quality")
    assert quality["met"] is False
