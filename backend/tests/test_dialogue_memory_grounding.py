from app.dialogue_memory import advance, delivered
from app.chat_turn import prepare


def test_question_cannot_replace_measurement_or_start_new_episode():
    state = advance({}, "u1", "Болит голова. Давление 124/82.")
    state = advance(state, "u2", "А давление 160/100? Если крутит живот, что делать?")
    assert state["topic"] == "headache"
    assert [(f["value"], f["user_message_id"]) for f in state["facts"]
            if f["key"] == "blood_pressure"] == [([124, 82], "u1")]
    assert not any(f["user_message_id"] == "u2" for f in state["facts"])


def test_change_to_last_answer_keeps_real_user_source():
    state = advance({}, "u1", "После еды крутит живот. Спустя пять часов стало хуже.")
    state = delivered(state, "a1", "Можете ли пить?")
    state = advance(state, "u2", "Диареи нет, пить могу.")
    active = {f["key"]: f for f in state["facts"] if f["status"] == "active"}
    assert active["fluid_tolerance"]["value"] is True
    assert active["fluid_tolerance"]["question_id"] == "a1"
    assert active["diarrhea"]["kind"] == "denial"
    assert active["reported_interval"]["user_message_id"] == "u1"
    assert state["open_question"]["resolved_by"] == "u2"


def test_meal_time_is_not_pain_onset():
    state = advance({}, "u1", "Утром я съел пасту. Спустя пять часов начал крутить живот.")
    active = {f["key"]: f for f in state["facts"] if f["status"] == "active"}
    assert "onset" not in active
    assert active["reported_interval"]["value"] == "спустя пять часов"


def test_short_negative_answers_dehydration_check_and_advances_food_dialogue():
    state = advance({}, "u1", "Болит живот, съел не свежую еду, боль 5/10")
    state = delivered(state, "a1", "Когда ты начал чувствовать боль?")
    state = advance(state, "u2", "10 минут назад")
    previous = ("Следующий шаг: Проверь, не было ли у тебя признаков обезвоживания — "
                "сухость во рту, уменьшение мочеиспускания.")
    state = delivered(state, "a2", previous)
    state = advance(state, "u3", "не было")
    fact = next(f for f in state["facts"] if f["key"] == "dehydration" and f["status"] == "active")
    assert fact["value"] is False and fact["question_id"] == "a2"
    assert state["open_question"]["status"] == "resolved"
    turn = prepare("не было", previous, state, None, [], {})
    assert turn.move == "food_update"
    assert "vomited" in turn.required.casefold()
    assert turn.source_refs


def test_no_answers_drinking_question_without_repeating_it():
    state = delivered(advance({}, "u1", "Болит живот"), "a1", "Ты уже пил?")
    state = advance(state, "u2", "нет")
    fact = next(f for f in state["facts"] if f["key"] == "fluid_intake" and f["status"] == "active")
    assert fact["value"] is False and fact["question_id"] == "a1"
    turn = prepare("нет", "Ты уже пил?", state, None, [], {})
    assert turn.move == "food_update"
    assert "do not ask again" in turn.required


def test_abdominal_pain_resolution_and_recurrence_start_fresh_facts():
    state = advance({}, "u1", "Болит живот, боль 5/10")
    state = advance(state, "u2", "живот прошел")
    assert state["episode_resolved"] is True
    assert state["last_update"]["kind"] == "resolution"
    assert prepare("живот прошел", "", state, None, [], {}).move == "resolution"
    state = advance(state, "u3", "нет боли и других признаков")
    assert state["last_update"]["kind"] == "resolution_confirmed"
    state = advance(state, "u4", "Снова болит живот, боль 2/10")
    assert state["last_update"]["kind"] == "new_topic"
    assert {f["user_message_id"] for f in state["facts"] if f["status"] == "active"} == {"u4"}
