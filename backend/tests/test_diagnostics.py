import asyncio
import json
from pathlib import Path

import httpx

from app.db import sqlite_url
from app.main import create_app


def test_request_and_browser_events_are_logged_without_payloads(tmp_path: Path) -> None:
    async def exercise() -> None:
        app = create_app(
            database_url=sqlite_url(tmp_path / "test.sqlite3"),
            log_dir=tmp_path / "logs",
        )
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/v1/client-events",
                    json={"code": "form_failure", "request_id": "ui-test"},
                )
                assert response.status_code == 204
                assert response.headers["X-Request-ID"]
                invalid = await client.post(
                    "/api/v1/crew", json={"display_name": "PRIVATE-TEST-MARKER", "fictional": False}
                )
                assert invalid.status_code == 422

    asyncio.run(exercise())
    log_path = tmp_path / "logs" / "astra.jsonl"
    content = log_path.read_text(encoding="utf-8")
    entries = [json.loads(line) for line in content.splitlines()]
    assert "PRIVATE-TEST-MARKER" not in content
    assert any(item["event"] == "client_event" and item["code"] == "form_failure" for item in entries)
    assert any(item["event"] == "http_request" and item["status"] == 422 for item in entries)
    assert any(item["event"] == "service_start" for item in entries)
    assert any(item["event"] == "service_stop" for item in entries)
