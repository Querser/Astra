"""Replay two reported failures through the real local model and isolated API."""
from pathlib import Path
from tempfile import TemporaryDirectory
import re
import sys

from fastapi.testclient import TestClient

from app.db import sqlite_url
from app.main import create_app


def main():
    conversations = [
        ["\u0423 \u043c\u0435\u043d\u044f \u0431\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430", "\u0441\u0435\u0439\u0447\u0430\u0441. 2/10. \u0423\u0434\u0430\u0440\u0438\u043b\u0441\u044f. \u041a\u0440\u043e\u0432\u0438 \u043d\u0435\u0442, \u043d\u0435\u0431\u043e\u043b\u044c\u0448\u0430\u044f \u0448\u0438\u0448\u043a\u0430 \u043f\u043e\u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f",
         "\u041f\u0440\u0438\u043b\u043e\u0436\u0438\u043b \u043b\u0435\u0434", "\u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u043e"],
        ["\u0411\u043e\u043b\u0438\u0442 \u0440\u0443\u043a\u0430", "\u043f\u043e\u0440\u0435\u0437\u0430\u043b\u0441\u044f", "\u043f\u0430\u043b\u0435\u0446, \u043a\u0440\u043e\u0432\u0438 \u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442, \u0441\u043e\u0437\u043d\u0430\u043d\u0438\u0435 \u0432 \u043f\u043e\u0440\u044f\u0434\u043a\u0435, \u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430 \u0432 \u043f\u043e\u0440\u044f\u0434\u043a\u0435, \u043f\u043e\u0440\u0435\u0437\u0430\u043b\u0441\u044f 3 \u043c\u0438\u043d\u0443\u0442\u044b \u043d\u0430\u0437\u0430\u0434",
         "\u0443 \u043c\u0435\u043d\u044f \u043f\u043e\u0432\u044b\u0448\u0435\u043d\u0430 \u0442\u0435\u043c\u043f\u0438\u0440\u0430\u0442\u0443\u0440\u0430", "\u044f \u0442\u0435\u0431\u0435 \u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0442\u043e \u043f\u0438\u0441\u0430\u043b \u043f\u0440\u043e \u043f\u043e\u0440\u0435\u0437",
         "\u0434\u0430 \u044f \u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0442\u043e \u043f\u043e\u0440\u0435\u0437\u0430\u043b\u0441\u044f, \u043d\u0435 \u0434\u0443\u043c\u0430\u044e, \u0447\u0442\u043e \u044d\u0442\u043e \u0438\u0437 \u0437\u0430 \u043f\u043e\u0440\u0435\u0437\u0430", "\u0436\u0430\u0440",
         "\u0432\u044b\u043f\u043e\u043b\u043d\u044f\u044e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f \u043f\u043e \u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0435 \u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\u0435\u043d\u0438\u044f"],
        ["\u0431\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430", "\u0447\u0430\u0441 \u043d\u0430\u0437\u0430\u0434, 10/10", "\u043d\u0438\u0447\u0435\u0433\u043e", "\u0448\u0435\u044f \u043e\u043f\u0443\u0445\u043b\u0430", "\u0447\u0442\u043e \u0441\u043e \u043c\u043d\u043e\u0439?"],
        ["\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435 \u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10", "10 \u043c\u0438\u043d\u0443\u0442 \u043d\u0430\u0437\u0430\u0434", "\u043d\u0435 \u0431\u044b\u043b\u043e"],
        ["\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435 \u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10", "\u0436\u0438\u0432\u043e\u0442 \u043f\u0440\u043e\u0448\u0435\u043b", "\u043d\u0435\u0442 \u0431\u043e\u043b\u0438 \u0438 \u0434\u0440\u0443\u0433\u0438\u0445 \u043f\u0440\u0438\u0437\u043d\u0430\u043a\u043e\u0432"],
    ]
    with TemporaryDirectory(prefix="astra-reported-chat-") as directory:
        app = create_app(database_url=sqlite_url(Path(directory) / "demo.sqlite3"), log_dir=Path(directory) / "logs")
        with TestClient(app) as client:
            for index, conversation in enumerate(conversations):
                if len(sys.argv) > 1 and index != int(sys.argv[1]):
                    continue
                crew = client.post("/api/v1/crew", json={"display_name": f"Conversation check {index}"})
                crew.raise_for_status()
                crew_id = crew.json()["id"]
                answers = []
                for prompt in conversation:
                    response = client.post("/api/v1/assistant/chat", json={"crew_member_id": crew_id, "message": prompt})
                    response.raise_for_status()
                    reply = response.json()["messages"][1]
                    print(index, prompt, "=>", reply["body"], "|", reply["citations"])
                    if reply["engine"] != "local_model:qwen3:8b":
                        print((Path(directory) / "logs" / "astra.jsonl").read_text(encoding="utf-8")[-3500:])
                    assert reply["engine"] == "local_model:qwen3:8b", reply
                    assert not re.search(r"\*\*|^\s*[-•]\s", reply["body"], re.M), reply
                    assert not any("RADIATION" in citation or "ISOLATION" in citation for citation in reply["citations"]), reply
                    answers.append(reply["body"])
                if index == 0:
                    assert not re.search(r"how (?:do|are) you feel", answers[-1], re.I), answers[-1]
                elif index == 1:
                    assert not re.search(r"severe (?:external )?bleeding", answers[-1], re.I), answers[-1]
                    assert re.search(r"temperature|fever|heat", " ".join(answers[3:7]), re.I)
                elif index == 2:
                    assert "10/10" in " ".join(answers[1:]) and re.search(r"urgent|immediate", answers[-1], re.I)
                    assert re.search(r"migraine|meningitis|hemorrhage|bleed", answers[-1], re.I)
                    assert "external bleeding" not in answers[-1].casefold()
                    record = client.get(f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
                    assert record["source_report_id"] and record["assessment"] == answers[-1]
                    assert any("\u0448\u0435\u044f \u043e\u043f\u0443\u0445\u043b\u0430" in item for item in record["symptoms"])
                elif index == 3:
                    assert answers[-1] != answers[-2]
                else:
                    assert not re.search(r"confirm again|are the symptoms gone\?|is the pain really gone\?", " ".join(answers[1:]), re.I)
                    record = client.get(f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
                    assert record["status"] == "resolved_by_user_report"


if __name__ == "__main__":
    main()
