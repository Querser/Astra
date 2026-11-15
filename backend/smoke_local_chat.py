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
            greeting = await client.post("/api/v1/assistant/chat", json={"crew_member_id": regression_crew, "message": "\u041f\u0440\u0438\u0432\u0435\u0442"})
            complaint = await client.post("/api/v1/assistant/chat", json={
                "crew_member_id": regression_crew,
                "message": "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430, \u043f\u043e\u0432\u044b\u0448\u0435\u043d\u043d\u0430\u044f \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430.",
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
                "\u0423\u0442\u0440\u043e\u043c \u044f \u0441\u044a\u0435\u043b \u043f\u0430\u0441\u0442\u0443, \u043a\u043e\u0442\u043e\u0440\u0430\u044f \u043f\u043e\u043a\u0430\u0437\u0430\u043b\u0430\u0441\u044c \u0442\u0443\u0445\u043b\u043e\u0439. \u0421\u043f\u0443\u0441\u0442\u044f \u043f\u044f\u0442\u044c \u0447\u0430\u0441\u043e\u0432 \u043d\u0430\u0447\u0430\u043b \u043a\u0440\u0443\u0442\u0438\u0442\u044c \u0436\u0438\u0432\u043e\u0442.",
                "\u0423\u0442\u0440\u043e\u043c \u044f \u0441\u044a\u0435\u043b \u043f\u0430\u0441\u0442\u0443, \u043a\u043e\u0442\u043e\u0440\u0430\u044f \u043f\u043e\u043a\u0430\u0437\u0430\u043b\u0430\u0441\u044c \u0442\u0443\u0445\u043b\u043e\u0439. \u0421\u043f\u0443\u0441\u0442\u044f \u043f\u044f\u0442\u044c \u0447\u0430\u0441\u043e\u0432 \u043d\u0430\u0447\u0430\u043b \u043a\u0440\u0443\u0442\u0438\u0442\u044c \u0436\u0438\u0432\u043e\u0442.",
                "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430, \u0443\u0434\u0430\u0440\u0438\u043b\u0441\u044f \u043f\u0430\u0440\u0443 \u043c\u0438\u043d\u0443\u0442 \u043d\u0430\u0437\u0430\u0434, \u043a\u0440\u043e\u0432\u0438 \u043d\u0435\u0442. \u0413\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0435, \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 \u0432 \u043d\u043e\u0440\u043c\u0435.",
                "\u0411\u043e\u043b\u044c 4 \u0438\u0437 10, \u0431\u043e\u043b\u044c\u0448\u0435 \u043d\u0438\u0447\u0435\u0433\u043e \u0438\u0437 \u043f\u0435\u0440\u0435\u0447\u0438\u0441\u043b\u0435\u043d\u043d\u043e\u0433\u043e \u043d\u0435\u0442.",
                "\u0423 \u043c\u0435\u043d\u044f \u0438\u0434\u0451\u0442 \u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\u0435\u043d\u0438\u0435. \u041f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443 \u0432\u043e\u0437\u043b\u0435 \u0437\u0430\u043f\u044f\u0441\u0442\u044c\u044f, \u043a\u0440\u043e\u0432\u044c \u0438\u0434\u0451\u0442. \u041f\u0440\u0435\u0434\u043c\u0435\u0442\u0430 \u0432 \u0440\u0430\u043d\u0435 \u043d\u0435\u0442.",
                "\u041a\u0440\u043e\u0432\u044c \u0431\u044c\u0451\u0442 \u0444\u043e\u043d\u0442\u0430\u043d\u043e\u043c, \u043f\u0440\u0438\u043b\u043e\u0436\u0438\u043b \u0447\u0438\u0441\u0442\u044b\u0439 \u0431\u0438\u043d\u0442. \u041e\u043d\u0435\u043c\u0435\u043d\u0438\u044f \u043d\u0435\u0442, \u0440\u0430\u043d\u0430 \u043d\u0435\u0433\u043b\u0443\u0431\u043e\u043a\u0430\u044f, \u043f\u043e\u043c\u043e\u0449\u044c \u0432 \u043f\u0443\u0442\u0438.",
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
