"""Check that the installed local model sees a multi-metric fictional profile."""

import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
from sqlalchemy import select

from app.db import sqlite_url, upgrade_database
from app.forecast_demo_seed import GRADUAL_NAME, seed_forecast_profiles
from app.main import create_app
from app.models import CrewMember


async def main() -> None:
    with TemporaryDirectory(prefix="astra-profile-smoke-") as directory:
        url = sqlite_url(Path(directory) / "smoke.sqlite3")
        upgrade_database(url)
        app = create_app(database_url=url)
        try:
            with app.state.database.session_factory() as session:
                seed_forecast_profiles(session)
                crew = session.scalar(select(CrewMember).where(
                    CrewMember.display_name == GRADUAL_NAME))
                crew_id = crew.id
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                response = await client.post("/api/v1/assistant/chat", json={
                    "crew_member_id": crew_id,
                    "message": "\u041f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u0432\u0441\u0435 \u043c\u043e\u0438 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u0438 \u043f\u0440\u043e\u0433\u043d\u043e\u0437\u044b: \u0447\u0442\u043e \u0438\u0437\u043c\u0435\u043d\u0438\u043b\u043e\u0441\u044c, \u0447\u0442\u043e \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0432\u043d\u0438\u043c\u0430\u043d\u0438\u044f \u0438 \u043f\u043e\u0447\u0435\u043c\u0443?",
                })
                assert response.status_code == 201, response.text
                assistant = response.json()["messages"][1]
                print(assistant["engine"], assistant["body"])
                assert assistant["engine"] == "local_model:qwen3:8b"
                assert len(assistant["body"]) > 80
                assert "bleeding" not in assistant["body"].casefold()
                assert any(word in assistant["body"].casefold() for word in ("pulse", "heart rate"))
                assert any(word in assistant["body"].casefold() for word in ("activity", "steps"))
                for message in ("\u041f\u0440\u0438\u0432\u0435\u0442", "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430", "\u041d\u0430\u0447\u0430\u043b\u0430\u0441\u044c \u043f\u043e\u043b\u0447\u0430\u0441\u0430 \u043d\u0430\u0437\u0430\u0434 \u043f\u043e\u0441\u0442\u0435\u043f\u0435\u043d\u043d\u043e, \u0431\u043e\u043b\u044c 4 \u0438\u0437 10. \u0423\u0434\u0430\u0440\u0430 \u043d\u0435 \u0431\u044b\u043b\u043e."):
                    response = await client.post("/api/v1/assistant/chat", json={
                        "crew_member_id": crew_id, "message": message,
                    })
                    assert response.status_code == 201, response.text
                    turn = response.json()["messages"][1]
                    print(turn["engine"], turn["body"])
                    assert turn["engine"] == "local_model:qwen3:8b"
                    body = turn["body"].casefold()
                    if message == "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430":
                        assert "?" in body and any(term in body for term in ("when", "start", "severe", "sudden", "intensity"))
                    elif message.startswith("\u041d\u0430\u0447\u0430\u043b\u0430\u0441\u044c"):
                        assert any(term in body for term in ("half an hour", "gradual", "moderate", "4", "30 minutes"))
        finally:
            app.state.database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
