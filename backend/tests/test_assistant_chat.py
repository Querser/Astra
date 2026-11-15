"""The conversation preserves turns, profile boundaries and sourced conclusions."""

import asyncio
import io
import json
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

from app.chat_engine import reply_to_message
from app.complaint_parser import explicit_measurements, symptom_codes
from app.db import sqlite_url, upgrade_database
from app.main import create_app
from app.models import Observation, ChatMemory, ChatMessage
from app.smart_chat import LocalChatModel, current_episode, explicit_topic, respond


@pytest.fixture
def app(tmp_path: Path):
    url = sqlite_url(tmp_path / "chat.sqlite3")
    upgrade_database(url)
    application = create_app(database_url=url, chat_model_enabled=False)
    yield application
    application.state.database.dispose()


def call(app, method: str, path: str, body: dict | None = None) -> httpx.Response:
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.request(method, path, json=body)
    return asyncio.run(send())


def test_followup_head_injury_and_profile_isolation(app):
    first = call(app, "POST", "/api/v1/crew", {"display_name": "First fictional crew"}).json()["id"]
    second = call(app, "POST", "/api/v1/crew", {"display_name": "Second fictional crew"}).json()["id"]
    opening = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": first, "message": "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430"})
    assert opening.status_code == 201, opening.text
    assert opening.json()["messages"][1]["citations"]
    followup = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": first, "message": "\u0423\u0434\u0430\u0440\u0438\u043b\u0441\u044f \u0435\u044e, \u0442\u0435\u043f\u0435\u0440\u044c \u0442\u043e\u0448\u043d\u0438\u0442"})
    assert followup.status_code == 201, followup.text
    assert "nhs.uk" in str(followup.json()["messages"][1]["citations"])
    assert followup.json()["messages"][1]["citations"]
    history = call(app, "GET", f"/api/v1/assistant/chat/{first}").json()
    assert [row["role"] for row in history] == ["user", "assistant", "user", "assistant"]
    assert call(app, "GET", f"/api/v1/assistant/chat/{second}").json() == []


def test_chat_episode_is_recorded_and_resolved_for_analysis(app):
    crew_id = call(app, "POST", "/api/v1/crew", {"display_name": "Resolution example"}).json()["id"]
    opening = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "Болит голова"})
    assert opening.status_code == 201, opening.text
    source_id = opening.json()["messages"][0]["source_report_id"]
    assert source_id
    update = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "Приложил лёд"})
    assert update.status_code == 201, update.text
    resolved = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "Боль прошла"})
    assert resolved.status_code == 201, resolved.text
    episode = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
    assert episode["source_report_id"] == source_id
    assert episode["status"] == "resolved_by_user_report"
    assert "Приложил лёд" in episode["helped"]
    assert episode["assessment"]
    assert call(app, "GET", f"/api/v1/assistant/chat/{crew_id}").json()[0]["source_report_id"] == source_id
    refreshed = call(app, "POST", "/api/v1/analysis/run", {"crew_member_id": crew_id})
    assert refreshed.status_code in (200, 201), refreshed.text
    assert source_id not in refreshed.json()["input_ids"]


def test_one_resolved_symptom_does_not_clear_another_active_symptom(app):
    crew_id = call(app, "POST", "/api/v1/crew", {"display_name": "Partial resolution example"}).json()["id"]
    for message in ("Болит голова", "Шея опухла", "Боль прошла"):
        result = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": message})
        assert result.status_code == 201, result.text
    episode = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
    assert episode["status"] == "active"
    final = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "Всё прошло"})
    assert final.status_code == 201, final.text
    episode = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"][-1]
    assert episode["status"] == "resolved_by_user_report"


def test_abdominal_complaint_closes_and_recurs_as_new_medical_episode(app):
    crew_id = call(app, "POST", "/api/v1/crew", {"display_name": "Abdominal recurrence example"}).json()["id"]
    first = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id,
                                                   "message": "Болит живот, съел несвежую еду, боль 5/10"})
    assert first.status_code == 201, first.text
    resolved = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "живот прошел"})
    assert resolved.status_code == 201, resolved.text
    episodes = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"]
    assert episodes[-1]["status"] == "resolved_by_user_report"
    again = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id,
                                                   "message": "Снова болит живот, боль 2/10"})
    assert again.status_code == 201, again.text
    episodes = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"]
    assert len(episodes) == 2
    assert episodes[0]["status"] == "resolved_by_user_report"
    assert episodes[1]["status"] == "active"
    assert episodes[0]["source_report_id"] != episodes[1]["source_report_id"]


def test_old_same_topic_recurrence_is_repaired_before_new_summary(app):
    crew_id = call(app, "POST", "/api/v1/crew", {"display_name": "Legacy recurrence example"}).json()["id"]
    first = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id, "message": "Болит живот"})
    assert first.status_code == 201
    old_id = first.json()["messages"][0]["source_report_id"]
    assert call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id,
                                                         "message": "живот прошел"}).status_code == 201
    with app.state.database.session_factory() as session:
        row = session.get(ChatMemory, crew_id)
        memory = json.loads(row.content_json)
        memory["medical_history"][-1]["status"] = "active"
        memory.pop("episode_resolved", None)
        row.content_json = json.dumps(memory, ensure_ascii=False)
        latest = session.query(ChatMessage).filter(ChatMessage.crew_member_id == crew_id).order_by(ChatMessage.created_at.desc()).first()
        later_at = latest.created_at + timedelta(seconds=1)
        repeated = ChatMessage(crew_member_id=crew_id, role="user", body="Снова болит живот, боль 2/10",
                               source_report_id=old_id, created_at=later_at)
        reply = ChatMessage(crew_member_id=crew_id, role="assistant", body="Ты уже пил?",
                            source_report_id=old_id, engine="local_model:qwen3:8b",
                            created_at=later_at + timedelta(seconds=1))
        session.add_all([repeated, reply])
        session.commit()
    summary = call(app, "POST", "/api/v1/assistant/chat", {"crew_member_id": crew_id,
                                                      "message": "Проанализируй мои измерения и прогнозы"})
    assert summary.status_code == 201, summary.text
    episodes = call(app, "GET", f"/api/v1/assistant/chat/{crew_id}/memory").json()["medical_history"]
    assert len(episodes) == 2
    assert episodes[0]["status"] == "resolved_by_user_report"
    assert episodes[1]["status"] == "active"
    assert episodes[1]["source_report_id"] != old_id
    assert summary.json()["messages"][0]["source_report_id"] is None


def test_isolated_low_oxygen_is_described_as_recovered():
    start = datetime(2026, 11, 1, 8)
    observations = [Observation(
        id=str(index), crew_member_id="demo", source_id="demo", metric="spo2",
        value_kind="scalar", scalar_value=float(value), unit="%",
        observed_at=start + timedelta(days=index), observed_offset_minutes=0,
        synthetic=True, quality_flags_json='["synthetic_ui_entry"]',
    ) for index, value in enumerate((91, 98, 98, 97, 99, 98, 97, 98))]
    answer, sources = reply_to_message(["SpO\u2082"], observations, {})
    assert "95" in answer
    assert "91" in answer and "97" in answer and "99" in answer
    assert sources and "fda.gov" in sources[0]
    assert explicit_measurements("SpO\u2082 98%") == [{"metric": "spo2", "value_kind": "scalar", "scalar_value": 98.0, "unit": "%"}]


def test_bleeding_word_order_negation_and_no_embedded_object():
    positive = "\u041f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443. \u041a\u0440\u043e\u0432\u044c \u0442\u0435\u0447\u0435\u0442 \u0444\u043e\u043d\u0442\u0430\u043d\u043e\u043c, \u043f\u0440\u0435\u0434\u043c\u0435\u0442\u043e\u0432 \u0432 \u0440\u0430\u043d\u0435 \u043d\u0435\u0442"
    assert "external_bleeding" in symptom_codes(positive)
    assert "external_bleeding" not in symptom_codes("\u041a\u0440\u043e\u0432\u044c \u043d\u0435 \u0442\u0435\u0447\u0435\u0442")
    answer, sources = reply_to_message([positive], [], {})
    assert "no object in the wound" in answer.lower()
    assert any("nhs.uk" in url for url in sources)


def test_spoiled_food_is_analyzed_on_first_turn_and_repetition():
    message = "Утром я съел пасту, которая показалась тухлой. Спустя пять часов начал крутить живот."
    first, sources, engine = respond([message], [], {}, None)
    second, _, _ = respond([message, message], [], {}, None)
    assert "food poisoning" in first.lower() and "5 h" in first
    assert "water" in first.lower() and "diarrhea" in first.lower()
    assert "nhs.uk" in str(sources) and engine == "offline_rules"
    assert second != first and "already" in second.lower() and "food poisoning" in second.lower()


def test_head_impact_followup_merges_severity_and_negated_bleeding_without_food_context():
    food = "Съел тухлую пасту, крутит живот"
    head = "Болит голова, ударился пару минут назад, крови нет. Головокружение, состояние в норме."
    followup = "Боль 4 из 10, больше ничего из перечисленного нет."
    topic, episode = current_episode([food, head, followup])
    assert topic == "head" and episode == [head, followup]
    answer, sources, _ = respond([food, head, followup], [], {}, None)
    assert "concussion" in answer.lower() and "4/10" in answer
    assert "no external bleeding" in answer.lower()
    assert "no other listed symptoms" in answer.lower()
    assert "food poisoning" not in answer.lower()
    assert "nice.org.uk" in str(sources)


def test_model_cannot_insert_an_unreported_pain_score():
    class InventingModel:
        model = "test-model"

        def extract(self, episode):
            return {"topic": "head", "head_impact": True, "spoiled_food": False,
                    "abdominal_pain": False, "headache": True, "dizziness": True,
                    "nausea": False, "vomiting": False, "diarrhea": False,
                    "bleeding": False, "severity_0_10": 4,
                    "food_to_symptoms_hours": None, "explicitly_no_other_symptoms": True}

    head = "Болит голова, ударился пару минут назад, крови нет. Головокружение, состояние в норме."
    answer, _, engine = respond([head], [], {}, InventingModel())
    assert "4/10" not in answer
    assert "no other listed symptoms" not in answer.lower()
    assert engine == "offline_rules"


def test_spurting_bleeding_followup_changes_urgency_and_next_action():
    opening = "Порезал руку возле запястья, кровь идёт. Предмета в ране нет."
    followup = "Кровь бьёт фонтаном, приложил чистый бинт, онемения нет, рана неглубокая, помощь в пути."
    first, _, _ = respond([opening], [], {}, None)
    second, _, _ = respond([opening, followup], [], {}, None)
    assert first != second
    assert "severe external bleeding" in second.lower()
    assert "help is on the way" in second.lower()
    assert "pressure" in second.lower()


def test_headache_with_subjective_fever_is_a_distinct_current_episode():
    message = "Болит голова, повышенная температура."
    assert explicit_topic(message) == "fever_headache"
    topic, episode = current_episode(["Привет", message])
    assert topic == "fever_headache"
    assert episode == ["Привет", message]


def test_enabled_model_failure_is_not_disguised_as_an_offline_medical_answer():
    class FailingEnabledModel:
        enabled = True
        model = "test-local-model"

        def generate(self, episode, conversation, observations, analysis, topic):
            return None

    answer, sources, engine = respond(
        ["Болит голова, повышенная температура."], [], {}, FailingEnabledModel(),
    )
    assert "analysis not performed" in answer.lower()
    assert sources == []
    assert engine == "local_model_error:test-local-model"


@pytest.mark.parametrize("first", [b"{", b'{"done_reason":"length","message":{"content":"partial"}}'])
def test_headache_retries_incomplete_response_without_requiring_json_from_model(monkeypatch, first):
    calls = []
    question = "When did the pain begin?"
    responses = iter([first, json.dumps({"message": {"content": question}}).encode()])

    def local_call(request, timeout):
        calls.append(json.loads(request.data))
        return io.BytesIO(next(responses))

    monkeypatch.setattr("app.smart_chat.urlopen", local_call)
    answer, _, engine = respond(["Привет", "Болит голова"], [], {}, LocalChatModel(enabled=True))
    assert answer == question and engine.startswith("local_model:")
    assert len(calls) == 2
    for payload in calls:
        assert "format" not in payload
        assert payload["messages"][-1]["content"].endswith("Болит голова")
