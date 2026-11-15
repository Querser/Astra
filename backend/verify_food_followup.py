"""Replay the reported short negative reply against the real local model."""
from uuid import uuid4
import json

from app.dialogue_memory import advance, delivered
from app.smart_chat import LocalChatModel


def main():
    opening = "\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435 \u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10"
    first_answer = "\u0411\u043e\u043b\u044c \u0432 \u0436\u0438\u0432\u043e\u0442\u0435 \u043f\u043e\u0441\u043b\u0435 \u0435\u0434\u044b — \u044d\u0442\u043e \u043f\u0440\u0438\u0437\u043d\u0430\u043a \u043f\u0438\u0449\u0435\u0432\u043e\u0433\u043e \u043e\u0442\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f. \u041a\u043e\u0433\u0434\u0430 \u0442\u044b \u043d\u0430\u0447\u0430\u043b \u0447\u0443\u0432\u0441\u0442\u0432\u043e\u0432\u0430\u0442\u044c \u0431\u043e\u043b\u044c?"
    second = "10 \u043c\u0438\u043d\u0443\u0442 \u043d\u0430\u0437\u0430\u0434"
    second_answer = ("\u0421\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433: \u041f\u0440\u043e\u0432\u0435\u0440\u044c, \u043d\u0435 \u0431\u044b\u043b\u043e \u043b\u0438 \u0443 \u0442\u0435\u0431\u044f \u043f\u0440\u0438\u0437\u043d\u0430\u043a\u043e\u0432 \u043e\u0431\u0435\u0437\u0432\u043e\u0436\u0438\u0432\u0430\u043d\u0438\u044f — "
                     "\u0441\u0443\u0445\u043e\u0441\u0442\u044c \u0432\u043e \u0440\u0442\u0443, \u0443\u043c\u0435\u043d\u044c\u0448\u0435\u043d\u0438\u0435 \u043c\u043e\u0447\u0435\u0438\u0441\u043f\u0443\u0441\u043a\u0430\u043d\u0438\u044f.")
    latest = "\u043d\u0435 \u0431\u044b\u043b\u043e"
    memory = advance({}, "u1", opening)
    memory = delivered(memory, "a1", first_answer)
    memory = advance(memory, "u2", second)
    memory = delivered(memory, "a2", second_answer)
    memory = advance(memory, "u3", latest)
    conversation = [
        {"role": "user", "content": opening, "id": "u1"},
        {"role": "assistant", "content": first_answer, "id": "a1"},
        {"role": "user", "content": second, "id": "u2"},
        {"role": "assistant", "content": second_answer, "id": "a2"},
        {"role": "user", "content": latest, "id": "u3"},
    ]
    model = LocalChatModel()
    result = model.generate([opening, second, latest], conversation, [], {}, "food",
                            memory=memory, request_id=str(uuid4()))
    assert result is not None, model.last_validation_error
    answer = result["answer"]
    assert answer != second_answer
    assert "dehydration" in answer.casefold() or "vomit" in answer.casefold(), answer
    print(json.dumps(answer, ensure_ascii=True))
    opening = "\u0411\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442, \u0441\u044a\u0435\u043b \u043d\u0435 \u0441\u0432\u0435\u0436\u0443\u044e \u0435\u0434\u0443, \u0431\u043e\u043b\u044c 5/10"
    first_answer = "\u041f\u0435\u0439 \u0432\u043e\u0434\u0443 \u043c\u0430\u043b\u0435\u043d\u044c\u043a\u0438\u043c\u0438 \u0433\u043b\u043e\u0442\u043a\u0430\u043c\u0438. \u0422\u044b \u0443\u0436\u0435 \u043f\u0438\u043b?"
    memory = delivered(advance({}, "u4", opening), "a4", first_answer)
    memory = advance(memory, "u5", "\u043d\u0435\u0442")
    conversation = [
        {"role": "user", "content": opening, "id": "u4"},
        {"role": "assistant", "content": first_answer, "id": "a4"},
        {"role": "user", "content": "\u043d\u0435\u0442", "id": "u5"},
    ]
    result = model.generate([opening, "\u043d\u0435\u0442"], conversation, [], {}, "food",
                            memory=memory, request_id=str(uuid4()))
    assert result is not None, model.last_validation_error
    assert "have you drunk" not in result["answer"].casefold(), result["answer"]
    print(json.dumps(result["answer"], ensure_ascii=True))


if __name__ == "__main__":
    main()
