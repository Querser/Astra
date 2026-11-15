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
                    "message": "Проанализируй все мои измерения и прогнозы: что изменилось, что требует внимания и почему?",
                })
                assert response.status_code == 201, response.text
                assistant = response.json()["messages"][1]
                print(assistant["engine"], assistant["body"])
                assert assistant["engine"] == "local_model:qwen3:8b"
                assert len(assistant["body"]) > 80
                assert "bleeding" not in assistant["body"].casefold()
                assert any(word in assistant["body"].casefold() for word in ("pulse", "heart rate"))
                assert any(word in assistant["body"].casefold() for word in ("activity", "steps"))
                for message in ("Привет", "Болит голова", "Началась полчаса назад постепенно, боль 4 из 10. Удара не было."):
                    response = await client.post("/api/v1/assistant/chat", json={
                        "crew_member_id": crew_id, "message": message,
                    })
                    assert response.status_code == 201, response.text
                    turn = response.json()["messages"][1]
                    print(turn["engine"], turn["body"])
                    assert turn["engine"] == "local_model:qwen3:8b"
                    body = turn["body"].casefold()
                    if message == "Болит голова":
                        assert "?" in body and any(term in body for term in ("when", "start", "severe", "sudden", "intensity"))
                    elif message.startswith("Началась"):
                        assert any(term in body for term in ("half an hour", "gradual", "moderate", "4", "30 minutes"))
        finally:
            app.state.database.dispose()


if __name__ == "__main__":
    asyncio.run(main())
