"""Real local-model check using a disposable database and packaged sources."""

from pathlib import Path
from tempfile import TemporaryDirectory
import json

from fastapi.testclient import TestClient

from app.db import sqlite_url
from app.main import create_app


def main() -> None:
    with TemporaryDirectory(prefix="astra-space-chat-") as directory:
        root = Path(directory)
        app = create_app(database_url=sqlite_url(root / "demo.sqlite3"), log_dir=root / "logs")
        with TestClient(app) as client:
            crew = client.post("/api/v1/crew", json={"display_name": "Research demo profile"})
            crew.raise_for_status()
            crew_id = crew.json()["id"]
            mission = client.patch(f"/api/v1/crew/{crew_id}/mission", json={
                "mission_location": "iss", "mission_phase": "orbit", "habitat": "Demo module"})
            mission.raise_for_status()
            turns = [
                "Какакая последняя записть про радиацию окружающей среды?",
                "Да, покажи",
                "Где данные?",
                "Как радиация на меня влияет?",
            ]
            output = []
            for question in turns:
                result = client.post("/api/v1/assistant/chat", json={
                    "crew_member_id": crew_id, "message": question,
                }, timeout=120)
                result.raise_for_status()
                reply = result.json()["messages"][1]
                print(question, "=>", reply["engine"], reply["body"])
                if reply["engine"] != "local_model:qwen3:8b":
                    print((root / "logs" / "astra.jsonl").read_text(encoding="utf-8")[-2200:])
                assert reply["engine"] == "local_model:qwen3:8b", reply
                output.append({"question": question, "answer": reply["body"],
                               "engine": reply["engine"], "citations": reply["citations"]})
            for row in output[:3]:
                assert any(ref.startswith("research:RadLab") for ref in row["citations"]), row
                assert "6.57" in row["answer"] and "01:04:40" in row["answer"], row
                assert "µGy/hour" in row["answer"], row
            assert "Showing." != output[1]["answer"].strip(), output[1]
            assert "12:45" not in output[3]["answer"] and "Martian" not in output[3]["answer"]
            assert "HRP.RISK.RADIATION_CANCER" in " ".join(output[3]["citations"]), output[3]
            assert not any(name.casefold() in output[3]["answer"].casefold()
                           for name in ("NASA", "Canadian Space Agency", "CSA", "OCHMO", "OSDR", "Inspiration4"))
            print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
