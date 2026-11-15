"""Collection conditions survive the normal manual observation lifecycle."""

import asyncio

import httpx

from app.db import sqlite_url, upgrade_database
from app.main import create_app


def send(app, method, path, payload=None):
    async def call():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=payload)
    return asyncio.run(call())


def test_manual_conditions_create_revision_reload_analysis(tmp_path):
    url = sqlite_url(tmp_path / "conditions.sqlite3")
    upgrade_database(url)
    app = create_app(database_url=url, chat_model_enabled=False)
    try:
        crew = send(app, "POST", "/api/v1/crew", {"display_name": "Test Crew"}).json()["id"]
        base = {"crew_member_id": crew, "metric": "heart_rate", "value": {"kind": "scalar", "amount": 72},
                "unit": "bpm", "observed_at": "2026-11-14T12:00:00+03:00"}
        old = send(app, "POST", "/api/v1/manual/observations", base)
        assert old.status_code == 201
        assert old.json()["measurement_context"] is None
        context = {"method": "Подсчёт вручную", "device": "Часы", "site": "запястье",
                   "activity_state": "покой", "posture": "сидя", "mission_phase": "orbit",
                   "habitat": "Модуль", "subjective": False, "baseline_status": "candidate",
                   "notes": "После отдыха"}
        created = send(app, "POST", "/api/v1/manual/observations", {**base,
            "observed_at": "2026-11-14T12:10:00+03:00", "measurement_context": context})
        assert created.status_code == 201, created.text
        ident = created.json()["id"]
        assert created.json()["measurement_context"] == context
        source = created.json()["source_id"]
        revision = send(app, "PATCH", f"/api/v1/observations/{ident}", {
            **{key: value for key, value in base.items() if key != "crew_member_id"},
            "value": {"kind": "scalar", "amount": 74}, "source_id": source,
            "synthetic": False, "observed_at": "2026-11-14T12:10:00+03:00",
        })
        assert revision.status_code == 201, revision.text
        assert revision.json()["measurement_context"] == context
        reread = send(app, "GET", f"/api/v1/observations/{revision.json()['id']}")
        assert reread.json()["measurement_context"] == context
        analysis = send(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew})
        assert analysis.status_code == 201, analysis.text
        assessments = [item for item in analysis.json()["facts"] if item["kind"] == "parameter_assessment"]
        heart = next(item for item in assessments if item["metric"] == "heart_rate")
        assert heart["measurement_context"] == context
        assert "measurement_method" not in heart["missing_context"]
        assert "rest_or_activity_state" not in heart["missing_context"]
    finally:
        app.state.database.dispose()
