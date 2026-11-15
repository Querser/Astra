"""Independent checks for complaint provenance, ambiguity, corrections and profile persistence."""
from uuid import uuid4

import pytest

from app.dialogue_memory import advance, delivered
from app.db import sqlite_url, upgrade_database
from app.main import create_app
from test_assistant_chat import call


def active(m, key):
    return [f for f in m.get("facts", []) if f["key"] == key and f["status"] == "active"]


def test_questions_have_provenance_and_only_delivered_answers_resolve():
    state = advance({}, "u1", "Болит голова")
    state = delivered(state, "a1", "Возможна рвота. Есть ли рвота?")
    assert not active(state, "vomiting")
    state = advance(state, "u2", "нет")
    fact, = active(state, "vomiting")
    assert (fact["kind"], fact["user_message_id"], fact["question_id"]) == ("denial", "u2", "a1")
    assert state["open_question"]["status"] == "resolved"
    assert state["open_question"]["resolved_by"] == "u2"
    state = delivered(state, "a2", "Боль проходит или держится?")
    for i, msg in enumerate(("нет", "больно проходит")):
        state = advance(state, f"u{i+3}", msg)
        assert state["last_update"]["kind"] == "ambiguous"
        assert state["open_question"]["status"] == "unresolved"
        assert not active(state, "pain_course")


def test_facts_and_corrections_do_not_contaminate_other_topics():
    state = advance({}, "g", "Привет")
    for msg in ("нет", "3 из 10"):
        state = advance(state, "orphan", msg)
    assert state["facts"] == []
    state = advance(state, "u1", "Болит голова")
    state = delivered(state, "a1", "Сколько баллов из 10?")
    state = advance(state, "u2", "3 из 10, давление чуть выше нормы")
    assert active(state, "pain_score")[0]["value"] == 3
    assert active(state, "blood_pressure_description")[0]["kind"] == "qualitative"
    assert not active(state, "blood_pressure")
    state = advance(state, "u3", "Поправка, боль 2 из 10")
    assert active(state, "pain_score")[0]["user_message_id"] == "u3"
    assert any(f["value"] == 3 and f["status"] == "superseded" and f["user_message_id"] == "u2" for f in state["facts"])
    state = delivered(state, "a2", "Есть ли тошнота?")
    state = advance(state, "u4", "Не знаю")
    assert active(state, "nausea")[0]["kind"] == "uncertainty"
    state = advance(state, "u5", "Теперь после еды крутит живот")
    assert state["topic"] == "food"
    assert not active(state, "pain_score")
    assert not active(state, "blood_pressure_description")


def test_negation_scoped_to_the_symptom():
    state = advance({}, "u1", "Тошнота есть и рвоты нет")
    assert active(state, "nausea")[0]["value"] is True
    assert active(state, "vomiting")[0]["value"] is False
    state = advance({}, "u2", "Нет тошноты и рвоты")
    assert active(state, "nausea")[0]["value"] is False
    assert active(state, "vomiting")[0]["value"] is False


def test_persisted_milestone(monkeypatch, tmp_path):
    url = sqlite_url(tmp_path / "profiles.db")
    upgrade_database(url)
    app = create_app(database_url=url)
    try:
        a,b = [call(app,"POST","/api/v1/crew",{"display_name":"QA " + name}).json()["id"] for name in ("A","B")]
        monkeypatch.setattr("app.api.respond",lambda *args,**kwargs: ("Есть ли рвота?",[],"local_model:fixture"))
        payload = {"crew_member_id":a,"request_id":str(uuid4()),"message":"Болит голова"}
        reply = call(app,"POST","/api/v1/assistant/chat",payload)
        assert reply.status_code == 201,reply.text
        items = reply.json()["messages"]
        assert all(row["crew_member_id"] == a for row in items)
        replay = call(app,"POST","/api/v1/assistant/chat",payload)
        assert [r["id"] for r in replay.json()["messages"]] == [r["id"] for r in items]
        conflict = call(app,"POST","/api/v1/assistant/chat",{**payload, "message":"Новый текст"})
        assert conflict.status_code == 409
        app.state.database.dispose()
        app = create_app(database_url=url)
        mem = call(app,"GET",f"/api/v1/assistant/chat/{a}/memory").json()
        assert mem["open_question"]["assistant_message_id"] == items[-1]["id"]
        assert call(app,"GET",f"/api/v1/assistant/chat/{b}").json() == []
        records = call(app,"GET",f"/api/v1/symptoms?crew_member_id={a}").json()
        assert len(records) == 1 and records[0]["description"] == payload["message"]
        assert items[0]["source_report_id"] == records[0]["id"]
        monkeypatch.setattr("app.api.respond",lambda *args,**kwargs: ("Сохранено",[],"local_model:fixture"))
        answer = call(app,"POST","/api/v1/assistant/chat",{"crew_member_id":a,"message":"нет"}).json()
        mem = call(app,"GET",f"/api/v1/assistant/chat/{a}/memory").json()
        fact, = active(mem, "vomiting")
        assert fact["question_id"] == items[-1]["id"] and fact["user_message_id"] == answer["messages"][0]["id"]
    finally:
        app.state.database.dispose()
