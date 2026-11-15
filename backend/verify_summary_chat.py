"""Verify a model-authored measurement and forecast summary on synthetic data."""
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from fastapi.testclient import TestClient

from app.db import sqlite_url
from app.demo_seed import seed_demo_profiles
from app.main import create_app
import app.smart_chat as smart_chat
from app.chat_turn import time_constraints


def main():
    rejected = []
    original_validate = smart_chat.validate
    def trace(answer, turn):
        reason = original_validate(answer, turn)
        if reason:
            rejected.append({"reason": reason, "timings": list(time_constraints(answer)), "answer": answer})
        return reason
    smart_chat.validate = trace
    with TemporaryDirectory(prefix="astra-summary-check-") as directory:
        app = create_app(database_url=sqlite_url(Path(directory) / "demo.sqlite3"),
                         log_dir=Path(directory) / "logs")
        with TestClient(app) as client:
            with app.state.database.session_factory() as session:
                profile = seed_demo_profiles(session)[0]
            for message in ("Болит живот, съел несвежую еду, боль 5/10", "нет"):
                earlier = client.post("/api/v1/assistant/chat", json={"crew_member_id": profile["crew_id"], "message": message})
                earlier.raise_for_status()
            response = client.post("/api/v1/assistant/chat", json={
                "crew_member_id": profile["crew_id"],
                "message": "Проанализируй все мои измерения и прогнозы: что изменилось, что требует внимания и почему?",
            })
            response.raise_for_status()
            result = response.json()["messages"][1]
            if not result["engine"].startswith("local_model:"):
                print((Path(directory) / "logs" / "astra.jsonl").read_text(encoding="utf-8")[-3000:])
                print(json.dumps(rejected, ensure_ascii=True))
            assert result["engine"].startswith("local_model:"), result
            assert len(result["body"]) > 70, result
            print(json.dumps(result["body"], ensure_ascii=True))


if __name__ == "__main__":
    main()
