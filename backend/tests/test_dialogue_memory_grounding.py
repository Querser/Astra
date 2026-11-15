from app.dialogue_memory import advance, delivered
from app.chat_turn import prepare


def test_question_cannot_replace_measurement_or_start_new_episode():
    state = advance({}, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430. \u0414\u0430\u0432\u043b\u0435\u043d\u0438\u0435 124/82.")
    state = advance(state, "u2", "\u0410 \u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 160/100? \u0415\u0441\u043b\u0438 \u043a\u0440\u0443\u0442\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0447\u0442\u043e \u0434\u0435\u043b\u0430\u0442\u044c?")
    assert state["topic"] == "headache"
    assert [(f["value"], f["user_message_id"]) for f in state["facts"]
            if f["key"] == "blood_pressure"] == [([124, 82], "u1")]
    assert not any(f["user_message_id"] == "u2" for f in state["facts"])


def test_change_to_last_answer_keeps_real_user_source():
    state = advance({}, "u1", "\u041f\u043e\u0441\u043b\u0435 \u0435\u0434\u044b \u043a\u0440\u0443\u0442\u0438\u0442 \u0436\u0438\u0432\u043e\u0442. \u0421\u043f\u0443\u0441\u0442\u044f \u043f\u044f\u0442\u044c \u0447\u0430\u0441\u043e\u0432 \u0441\u0442\u0430\u043b\u043e \u0445\u0443\u0436\u0435.")
    state = delivered(state, "a1", "\u041c\u043e\u0436\u0435\u0442\u0435 \u043b\u0438 \u043f\u0438\u0442\u044c?")
    state = advance(state, "u2", "\u0414\u0438\u0430\u0440\u0435\u0438 \u043d\u0435\u0442, \u043f\u0438\u0442\u044c \u043c\u043e\u0433\u0443.")
    active = {f["key"]: f for f in state["facts"] if f["status"] == "active"}
    assert active["fluid_tolerance"]["value"] is True
    assert active["fluid_tolerance"]["question_id"] == "a1"
    assert active["diarrhea"]["kind"] == "denial"
    assert active["reported_interval"]["user_message_id"] == "u1"
    assert state["open_question"]["resolved_by"] == "u2"


def test_meal_time_is_not_pain_onset():
    state = advance({}, "u1", "\u0423\u0442\u0440\u043e\u043c \u044f \u0441\u044a\u0435\u043b \u043f\u0430\u0441\u0442\u0443. \u0421\u043f\u0443\u0441\u0442\u044f \u043f\u044f\u0442\u044c \u0447\u0430\u0441\u043e\u0432 \u043d\u0430\u0447\u0430\u043b \u043a\u0440\u0443\u0442\u0438\u0442\u044c \u0436\u0438\u0432\u043e\u0442.")
    active = {f["key"]: f for f in state["facts"] if f["status"] == "active"}
    assert "onset" not in active
    assert active["reported_interval"]["value"] == "\u0441\u043f\u0443\u0441\u0442\u044f \u043f\u044f\u0442\u044c \u0447\u0430\u0441\u043e\u0432"


def test_short_negative_answers_dehydration_check_and_advances_food_dialogue():
    state = advance({}, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435 \u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10")
    state = delivered(state, "a1", "\u041a\u043e\u0433\u0434\u0430 \u0442\u044b \u043d\u0430\u0447\u0430\u043b \u0447\u0443\u0432\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c \u0431\u043e\u043b\u044c?")
    state = advance(state, "u2", "10 \u043c\u0438\u043d\u0443\u0442 \u043d\u0430\u0437\u0430\u0434")
    previous = ("\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: \u041f\u0440\u043e\u0432\u0435\u0440\u044c, \u043d\u0435 \u0431\u044b\u043b\u043e \u043b\u0438 \u0443 \u0442\u0435\u0431\u044f \u043f\u0440\u0438\u0437\u043d\u0430\u043a\u043e\u0432 \u043e\u0431\u0435\u0437\u0432\u043e\u0436\u0438\u0432\u0430\u043d\u0438\u044f — "
                "\u0441\u0443\u0445\u043e\u0441\u0442\u044c \u0432\u043e \u0440\u0442\u0443, \u0443\u043c\u0435\u043d\u044c\u0448\u0435\u043d\u0438\u0435 \u043c\u043e\u0447\u0435\u0438\u0441\u043f\u0443\u0441\u043a\u0430\u043d\u0438\u044f.")
    state = delivered(state, "a2", previous)
    state = advance(state, "u3", "\u043d\u0435 \u0431\u044b\u043b\u043e")
    fact = next(f for f in state["facts"] if f["key"] == "dehydration" and f["status"] == "active")
    assert fact["value"] is False and fact["question_id"] == "a2"
    assert state["open_question"]["status"] == "resolved"
    turn = prepare("\u043d\u0435 \u0431\u044b\u043b\u043e", previous, state, None, [], {})
    assert turn.move == "food_update"
    assert "vomited" in turn.required.casefold()
    assert turn.source_refs


def test_no_answers_drinking_question_without_repeating_it():
    state = delivered(advance({}, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442"), "a1", "\u0422\u044b \u0443\u0436\u0435 \u043f\u0438\u043b?")
    state = advance(state, "u2", "\u043d\u0435\u0442")
    fact = next(f for f in state["facts"] if f["key"] == "fluid_intake" and f["status"] == "active")
    assert fact["value"] is False and fact["question_id"] == "a1"
    turn = prepare("\u043d\u0435\u0442", "\u0422\u044b \u0443\u0436\u0435 \u043f\u0438\u043b?", state, None, [], {})
    assert turn.move == "food_update"
    assert "do not ask again" in turn.required


def test_abdominal_pain_resolution_and_recurrence_start_fresh_facts():
    state = advance({}, "u1", "\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0431\u043e\u043b\u044c 5/10")
    state = advance(state, "u2", "\u0436\u0438\u0432\u043e\u0442 \u043f\u0440\u043e\u0448\u0435\u043b")
    assert state["episode_resolved"] is True
    assert state["last_update"]["kind"] == "resolution"
    assert prepare("\u0436\u0438\u0432\u043e\u0442 \u043f\u0440\u043e\u0448\u0435\u043b", "", state, None, [], {}).move == "resolution"
    state = advance(state, "u3", "\u043d\u0435\u0442 \u0431\u043e\u043b\u0438 \u0438 \u0434\u0440\u0443\u0433\u0438\u0445 \u043f\u0440\u0438\u0437\u043d\u0430\u043a\u043e\u0432")
    assert state["last_update"]["kind"] == "resolution_confirmed"
    state = advance(state, "u4", "\u0421\u043d\u043e\u0432\u0430 \u0431\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0431\u043e\u043b\u044c 2/10")
    assert state["last_update"]["kind"] == "new_topic"
    assert {f["user_message_id"] for f in state["facts"] if f["status"] == "active"} == {"u4"}
