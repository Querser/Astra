"""Replay the reported short negative reply against the real local model."""
from uuid import uuid4
import json

from app.dialogue_memory import advance, delivered
from app.smart_chat import LocalChatModel


def main():
    opening = "Болит живот, съел не свежую еду, боль 5/10"
    first_answer = "Боль в животе после еды — это признак пищевого отравления. Когда ты начал чувствовать боль?"
    second = "10 минут назад"
    second_answer = ("Следующий шаг: Проверь, не было ли у тебя признаков обезвоживания — "
                     "сухость во рту, уменьшение мочеиспускания.")
    latest = "не было"
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
    opening = "Болит живот, съел не свежую еду, боль 5/10"
    first_answer = "Пей воду маленькими глотками. Ты уже пил?"
    memory = delivered(advance({}, "u4", opening), "a4", first_answer)
    memory = advance(memory, "u5", "нет")
    conversation = [
        {"role": "user", "content": opening, "id": "u4"},
        {"role": "assistant", "content": first_answer, "id": "a4"},
        {"role": "user", "content": "нет", "id": "u5"},
    ]
    result = model.generate([opening, "нет"], conversation, [], {}, "food",
                            memory=memory, request_id=str(uuid4()))
    assert result is not None, model.last_validation_error
    assert "have you drunk" not in result["answer"].casefold(), result["answer"]
    print(json.dumps(result["answer"], ensure_ascii=True))


if __name__ == "__main__":
    main()
