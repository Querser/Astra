"""Build a small, explicitly synthetic behavior-tuning corpus for ASTRA.

This corpus is independent of the 24-case and 240-case evaluation files: it
reads only the local knowledge cards. It is insufficient for clinical claims.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CARDS = json.loads((ROOT / "docs/model-led/knowledge_cards.json").read_text(encoding="utf-8"))["cards"]
OUT = ROOT / "training/data/pilot_sft.jsonl"
SYSTEM = (
    "Ты ASTRA, локальный исследовательский ассистент экипажа. "
    "Учитывай реплики и отрицания. Используй только переданные локальные карточки. "
    "Верни JSON с candidate_ids, urgency, answer_ru и used_knowledge_ids. "
    "Названия заболеваний — предварительные версии, без придуманных фактов."
)
POS_URGENCY = {
    "BLEEDING": "emergency", "HEAD": "prompt_review", "FOOD": "routine",
    "OXYGEN": "prompt_review", "SANS": "prompt_review", "BONE": "routine",
    "MUSCLE": "routine", "RADIATION": "prompt_review", "SLEEP": "routine",
    "BP": "prompt_review",
}
PREFACES = [
    "Сообщение с борта: ", "Я на смене. ", "Уточняю своё состояние: ",
    "Передаю наблюдение: ", "Сегодня заметил следующее: ", "Из моего журнала: ",
]


def row(card: dict, user_text: str, ids: list[str], urgency: str,
        answer: str, purpose: str) -> dict:
    context = {
        "messages": [user_text],
        "local_cards": [{key: card[key] for key in
                         ("id", "name_ru", "evidence_for", "evidence_against",
                          "ask_if_unknown")}],
    }
    assistant = {"candidate_ids": ids, "urgency": urgency, "answer_ru": answer,
                 "used_knowledge_ids": [card["id"]] if ids else []}
    return {"purpose": purpose, "card_id": card["id"], "messages": [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        {"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)},
    ]}


def build() -> list[dict]:
    result = []
    for card in CARDS:
        family = card["id"].split(".")[-1]
        positive = "; ".join(card["evidence_for"])
        negative = card["evidence_against"]
        question = card["ask_if_unknown"][0]
        for index, preface in enumerate(PREFACES):
            evidence = positive
            # A positive card example is a claim about the signal/risk, not a confirmed diagnosis.
            user = preface + evidence + ". Дополнительные данные пока собираю."
            answer = (f"Предварительная версия: {card['name_ru']}. Основание — {evidence}. "
                      f"Следует уточнить: {question}.")
            result.append(row(card, user, [card["id"]], POS_URGENCY[family], answer,
                              "positive_source_phrase"))
        for index, preface in enumerate(PREFACES):
            evidence = negative[index % len(negative)] if negative else \
                f"нет измерения или жалобы, связанных с {card['name_ru']}"
            user = preface + evidence + ". Других сведений нет."
            answer = (f"По сообщённым сведениям версия «{card['name_ru']}» не подтверждается. "
                      f"Для проверки при необходимости уточните: {question}.")
            result.append(row(card, user, [], "routine", answer, "negative_or_missing"))
    return result


def main() -> None:
    examples = build()
    assert len(examples) == 120
    texts = [item["messages"][1]["content"] for item in examples]
    assert len(texts) == len(set(texts))
    heldout = []
    for name in ("eval_cases.json", "review_cases_240.json"):
        heldout.extend(json.loads((ROOT / "docs/model-led" / name).read_text(encoding="utf-8"))["cases"])
    heldout_texts = {message.casefold() for case in heldout for message in case["messages"]}
    assert all(text.casefold() not in heldout_texts for text in texts)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in examples) + "\n", encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"Wrote {len(examples)} behavior examples; sha256={digest}")


if __name__ == "__main__":
    main()
