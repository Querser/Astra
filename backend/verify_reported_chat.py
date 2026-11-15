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
        ["У меня болит голова", "сейчас. 2/10. Ударился. Крови нет, небольшая шишка появляется",
         "Приложил лед", "нормально"],
        ["Болит рука", "порезался", "палец, крови почти нет, сознание в порядке, температура в порядке, порезался 3 минуты назад",
         "у меня повышена темпиратура", "я тебе только что писал про порез",
         "да я только что порезался, не думаю, что это из за пореза", "жар",
         "выполняю действия по остановке кровотечения"],
        ["болит голова", "час назад, 10/10", "ничего", "шея опухла", "что со мной?"],
        ["Болит живот, съел не свежую еду, боль 5/10", "10 минут назад", "не было"],
        ["Болит живот, съел не свежую еду, боль 5/10", "живот прошел", "нет боли и других признаков"],
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
                    assert any("шея опухла" in item for item in record["symptoms"])
                elif index == 3:
                    assert answers[-1] != answers[-2]
                else:
                    assert not re.search(r"confirm again|are the symptoms gone\?|is the pain really gone\?", " ".join(answers[1:]), re.I)
                    record = client.get(f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
                    assert record["status"] == "resolved_by_user_report"


if __name__ == "__main__":
    main()
