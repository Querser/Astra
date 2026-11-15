"""Run the two reported dialogue cases through a temporary local API database."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx

from app.db import sqlite_url, upgrade_database
from app.main import create_app


async def main() -> None:
    with TemporaryDirectory(prefix="astra-chat-smoke-") as directory:
        url = sqlite_url(Path(directory) / "smoke.sqlite3")
        upgrade_database(url)
        app = create_app(database_url=url)
        answers = []
        try:
          async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            crew = (await client.post("/api/v1/crew", json={"display_name": "Temporary dialogue test"})).json()["id"]
            regression_crew = (await client.post("/api/v1/crew", json={"display_name": "Temporary fever regression"})).json()["id"]
            observation = await client.post("/api/v1/manual/observations", json={
                "crew_member_id": regression_crew,
                "metric": "body_temperature",
                "value": {"kind": "scalar", "amount": 36.6},
                "unit": "°C",
                "observed_at": (datetime.now(timezone.utc) - timedelta(hours=8)).isoformat(),
            })
            assert observation.status_code == 201, observation.text
            greeting = await client.post("/api/v1/assistant/chat", json={"crew_member_id": regression_crew, "message": "Привет"})
            complaint = await client.post("/api/v1/assistant/chat", json={
                "crew_member_id": regression_crew,
                "message": "Болит голова, повышенная температура.",
            })
            assert greeting.status_code == 201, greeting.text
            assert complaint.status_code == 201, complaint.text
            greeting_answer = greeting.json()["messages"][1]
            complaint_answer = complaint.json()["messages"][1]
            print(f"Greeting: {greeting_answer['engine']}; {greeting_answer['body']}")
            print(f"Fever regression: {complaint_answer['engine']}; {complaint_answer['body']}")
            assert greeting_answer["engine"] == "local_model:qwen3:8b"
            assert complaint_answer["engine"] == "local_model:qwen3:8b"
            assert "troubl" in greeting_answer["body"].casefold() or "help" in greeting_answer["body"].casefold()
            assert "temperatur" in complaint_answer["body"].casefold()
            assert "temperature is normal" not in complaint_answer["body"].casefold()
            messages = [
                "Утром я съел пасту, которая показалась тухлой. Спустя пять часов начал крутить живот.",
                "Утром я съел пасту, которая показалась тухлой. Спустя пять часов начал крутить живот.",
                "Болит голова, ударился пару минут назад, крови нет. Головокружение, состояние в норме.",
                "Боль 4 из 10, больше ничего из перечисленного нет.",
                "У меня идёт кровотечение. Порезал руку возле запястья, кровь идёт. Предмета в ране нет.",
                "Кровь бьёт фонтаном, приложил чистый бинт. Онемения нет, рана неглубокая, помощь в пути.",
            ]
            if os.getenv("ASTRA_SMOKE_BLEEDING_ONLY") == "1":
                messages = messages[-2:]
            for index, message in enumerate(messages, 1):
                response = await client.post("/api/v1/assistant/chat", json={"crew_member_id": crew, "message": message})
                assert response.status_code == 201, response.text
                answer = response.json()["messages"][1]
                print(f"Case {index}: {answer['engine']}; {answer['body'][:180].replace(chr(10), ' | ')}")
                answers.append(answer["body"])
                if os.getenv("ASTRA_SMOKE_BLEEDING_ONLY") != "1" and index in (1, 3, 4):
                    assert answer["engine"] == "local_model:qwen3:8b"
        finally:
          app.state.database.dispose()
        if os.getenv("ASTRA_SMOKE_BLEEDING_ONLY") == "1":
            assert answers[0] != answers[1]
            assert any(word in answers[1].casefold() for word in ("pressure", "press"))
            return
        assert "food poisoning" in answers[0].casefold() or "stomach" in answers[0].casefold()
        assert answers[1] != answers[0]
        assert "4/10" not in answers[2]
        assert "concussion" in answers[3].casefold() and "4/10" in answers[3]
        assert answers[5] != answers[4]
        assert any(word in answers[5].casefold() for word in ("pressure", "press"))


if __name__ == "__main__":
    asyncio.run(main())
