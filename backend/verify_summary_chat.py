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
            for message in ("\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435\u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10", "\u043d\u0435\u0442"):
                earlier = client.post("/api/v1/assistant/chat", json={"crew_member_id": profile["crew_id"], "message": message})
                earlier.raise_for_status()
            response = client.post("/api/v1/assistant/chat", json={
                "crew_member_id": profile["crew_id"],
                "message": "\u041f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u0432\u0441\u0435 \u043c\u043e\u0438 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u0438 \u043f\u0440\u043e\u0433\u043d\u043e\u0437\u044b: \u0447\u0442\u043e \u0438\u0437\u043c\u0435\u043d\u0438\u043b\u043e\u0441\u044c, \u0447\u0442\u043e \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0432\u043d\u0438\u043c\u0430\u043d\u0438\u044f \u0438 \u043f\u043e\u0447\u0435\u043c\u0443?",
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
