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
    state = advance({}, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430")
    state = delivered(state, "a1", "\u0412\u043e\u0437\u043c\u043e\u0436\u043d\u0430 \u0440\u0432\u043e\u0442\u0430. \u0415\u0441\u0442\u044c \u043b\u0438 \u0440\u0432\u043e\u0442\u0430?")
    assert not active(state, "vomiting")
    state = advance(state, "u2", "\u043d\u0435\u0442")
    fact, = active(state, "vomiting")
    assert (fact["kind"], fact["user_message_id"], fact["question_id"]) == ("denial", "u2", "a1")
    assert state["open_question"]["status"] == "resolved"
    assert state["open_question"]["resolved_by"] == "u2"
    state = delivered(state, "a2", "\u0411\u043e\u043b\u044c \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442 \u0438\u043b\u0438 \u0434\u0435\u0440\u0436\u0438\u0442\u0441\u044f?")
    for i, msg in enumerate(("\u043d\u0435\u0442", "\u0431\u043e\u043b\u044c\u043d\u043e \u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442")):
        state = advance(state, f"u{i+3}", msg)
        assert state["last_update"]["kind"] == "ambiguous"
        assert state["open_question"]["status"] == "unresolved"
        assert not active(state, "pain_course")


def test_facts_and_corrections_do_not_contaminate_other_topics():
    state = advance({}, "g", "\u041f\u0440\u0438\u0432\u0435\u0442")
    for msg in ("\u043d\u0435\u0442", "3 \u0438\u0437 10"):
        state = advance(state, "orphan", msg)
    assert state["facts"] == []
    state = advance(state, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430")
    state = delivered(state, "a1", "\u0421\u043a\u043e\u043b\u044c\u043a\u043e \u0431\u0430\u043b\u043b\u043e\u0432 \u0438\u0437 10?")
    state = advance(state, "u2", "3 \u0438\u0437 10, \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 \u0447\u0443\u0442\u044c \u0432\u044b\u0448\u0435 \u043d\u043e\u0440\u043c\u044b")
    assert active(state, "pain_score")[0]["value"] == 3
    assert active(state, "blood_pressure_description")[0]["kind"] == "qualitative"
    assert not active(state, "blood_pressure")
    state = advance(state, "u3", "\u041f\u043e\u043f\u0440\u0430\u0432\u043a\u0430, \u0431\u043e\u043b\u044c 2 \u0438\u0437 10")
    assert active(state, "pain_score")[0]["user_message_id"] == "u3"
    assert any(f["value"] == 3 and f["status"] == "superseded" and f["user_message_id"] == "u2" for f in state["facts"])
    state = delivered(state, "a2", "\u0415\u0441\u0442\u044c \u043b\u0438 \u0442\u043e\u0448\u043d\u043e\u0442\u0430?")
    state = advance(state, "u4", "\u041d\u0435 \u0437\u043d\u0430\u044e")
    assert active(state, "nausea")[0]["kind"] == "uncertainty"
    state = advance(state, "u5", "\u0422\u0435\u043f\u0435\u0440\u044c \u043f\u043e\u0441\u043b\u0435 \u0435\u0434\u044b \u043a\u0440\u0443\u0442\u0438\u0442 \u0436\u0438\u0432\u043e\u0442")
    assert state["topic"] == "food"
    assert not active(state, "pain_score")
    assert not active(state, "blood_pressure_description")


def test_negation_scoped_to_the_symptom():
    state = advance({}, "u1", "\u0422\u043e\u0448\u043d\u043e\u0442\u0430 \u0435\u0441\u0442\u044c \u0438 \u0440\u0432\u043e\u0442\u044b \u043d\u0435\u0442")
    assert active(state, "nausea")[0]["value"] is True
    assert active(state, "vomiting")[0]["value"] is False
    state = advance({}, "u2", "\u041d\u0435\u0442 \u0442\u043e\u0448\u043d\u043e\u0442\u044b \u0438 \u0440\u0432\u043e\u0442\u044b")
    assert active(state, "nausea")[0]["value"] is False
    assert active(state, "vomiting")[0]["value"] is False


def test_persisted_milestone(monkeypatch, tmp_path):
    url = sqlite_url(tmp_path / "profiles.db")
    upgrade_database(url)
    app = create_app(database_url=url)
    try:
        a,b = [call(app,"POST","/api/v1/crew",{"display_name":"QA " + name}).json()["id"] for name in ("A","B")]
        monkeypatch.setattr("app.api.respond",lambda *args,**kwargs: ("\u0415\u0441\u0442\u044c \u043b\u0438 \u0440\u0432\u043e\u0442\u0430?",[],"local_model:fixture"))
        payload = {"crew_member_id":a,"request_id":str(uuid4()),"message":"\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430"}
        reply = call(app,"POST","/api/v1/assistant/chat",payload)
        assert reply.status_code == 201,reply.text
        items = reply.json()["messages"]
        assert all(row["crew_member_id"] == a for row in items)
        replay = call(app,"POST","/api/v1/assistant/chat",payload)
        assert [r["id"] for r in replay.json()["messages"]] == [r["id"] for r in items]
        conflict = call(app,"POST","/api/v1/assistant/chat",{**payload, "message":"\u041d\u043e\u0432\u044b\u0439 \u0442\u0435\u043a\u0441\u0442"})
        assert conflict.status_code == 409
        app.state.database.dispose()
        app = create_app(database_url=url)
        mem = call(app,"GET",f"/api/v1/assistant/chat/{a}/memory").json()
        assert mem["open_question"]["assistant_message_id"] == items[-1]["id"]
        assert call(app,"GET",f"/api/v1/assistant/chat/{b}").json() == []
        records = call(app,"GET",f"/api/v1/symptoms?crew_member_id={a}").json()
        assert len(records) == 1 and records[0]["description"] == payload["message"]
        assert items[0]["source_report_id"] == records[0]["id"]
        monkeypatch.setattr("app.api.respond",lambda *args,**kwargs: ("\u0421\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e",[],"local_model:fixture"))
        answer = call(app,"POST","/api/v1/assistant/chat",{"crew_member_id":a,"message":"\u043d\u0435\u0442"}).json()
        mem = call(app,"GET",f"/api/v1/assistant/chat/{a}/memory").json()
        fact, = active(mem, "vomiting")
        assert fact["question_id"] == items[-1]["id"] and fact["user_message_id"] == answer["messages"][0]["id"]
    finally:
        app.state.database.dispose()
