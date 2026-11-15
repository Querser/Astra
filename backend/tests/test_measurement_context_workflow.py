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
        context = {"method": "\u041f\u043e\u0434\u0441\u0447\u0451\u0442 \u0432\u0440\u0443\u0447\u043d\u0443\u044e", "device": "\u0427\u0430\u0441\u044b", "site": "\u0437\u0430\u043f\u044f\u0441\u0442\u044c\u0435",
                   "activity_state": "\u043f\u043e\u043a\u043e\u0439", "posture": "\u0441\u0438\u0434\u044f", "mission_phase": "orbit",
                   "habitat": "\u041c\u043e\u0434\u0443\u043b\u044c", "subjective": False, "baseline_status": "candidate",
                   "notes": "\u041f\u043e\u0441\u043b\u0435 \u043e\u0442\u0434\u044b\u0445\u0430"}
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
