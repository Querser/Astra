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
    "\u0422\u044b ASTRA, \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0439 \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u0438\u0439 \u0430\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442 \u044d\u043a\u0438\u043f\u0430\u0436\u0430. "
    "\u0423\u0447\u0438\u0442\u044b\u0432\u0430\u0439 \u0440\u0435\u043f\u043b\u0438\u043a\u0438 \u0438 \u043e\u0442\u0440\u0438\u0446\u0430\u043d\u0438\u044f. \u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0435\u0440\u0435\u0434\u0430\u043d\u043d\u044b\u0435 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0438. "
    "\u0412\u0435\u0440\u043d\u0438 JSON \u0441 candidate_ids, urgency, answer_ru \u0438 used_knowledge_ids. "
    "\u041d\u0430\u0437\u0432\u0430\u043d\u0438\u044f \u0437\u0430\u0431\u043e\u043b\u0435\u0432\u0430\u043d\u0438\u0439 — \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u0432\u0435\u0440\u0441\u0438\u0438, \u0431\u0435\u0437 \u043f\u0440\u0438\u0434\u0443\u043c\u0430\u043d\u043d\u044b\u0445 \u0444\u0430\u043a\u0442\u043e\u0432."
)
POS_URGENCY = {
    "BLEEDING": "emergency", "HEAD": "prompt_review", "FOOD": "routine",
    "OXYGEN": "prompt_review", "SANS": "prompt_review", "BONE": "routine",
    "MUSCLE": "routine", "RADIATION": "prompt_review", "SLEEP": "routine",
    "BP": "prompt_review",
}
PREFACES = [
    "\u0421\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u0435 \u0441 \u0431\u043e\u0440\u0442\u0430: ", "\u042f \u043d\u0430 \u0441\u043c\u0435\u043d\u0435. ", "\u0423\u0442\u043e\u0447\u043d\u044f\u044e \u0441\u0432\u043e\u0451 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435: ",
    "\u041f\u0435\u0440\u0435\u0434\u0430\u044e \u043d\u0430\u0431\u043b\u044e\u0434\u0435\u043d\u0438\u0435: ", "\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u0437\u0430\u043c\u0435\u0442\u0438\u043b \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0435: ", "\u0418\u0437 \u043c\u043e\u0435\u0433\u043e \u0436\u0443\u0440\u043d\u0430\u043b\u0430: ",
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
            user = preface + evidence + ". \u0414\u043e\u043f\u043e\u043b\u043d\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0435 \u0434\u0430\u043d\u043d\u044b\u0435 \u043f\u043e\u043a\u0430 \u0441\u043e\u0431\u0438\u0440\u0430\u044e."
            answer = (f"\u041f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u0430\u044f \u0432\u0435\u0440\u0441\u0438\u044f: {card['name_ru']}. \u041e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0435 — {evidence}. "
                      f"\u0421\u043b\u0435\u0434\u0443\u0435\u0442 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u044c: {question}.")
            result.append(row(card, user, [card["id"]], POS_URGENCY[family], answer,
                              "positive_source_phrase"))
        for index, preface in enumerate(PREFACES):
            evidence = negative[index % len(negative)] if negative else \
                f"\u043d\u0435\u0442 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u0438\u043b\u0438 \u0436\u0430\u043b\u043e\u0431\u044b, \u0441\u0432\u044f\u0437\u0430\u043d\u043d\u044b\u0445 \u0441 {card['name_ru']}"
            user = preface + evidence + ". \u0414\u0440\u0443\u0433\u0438\u0445 \u0441\u0432\u0435\u0434\u0435\u043d\u0438\u0439 \u043d\u0435\u0442."
            answer = (f"\u041f\u043e \u0441\u043e\u043e\u0431\u0449\u0451\u043d\u043d\u044b\u043c \u0441\u0432\u0435\u0434\u0435\u043d\u0438\u044f\u043c \u0432\u0435\u0440\u0441\u0438\u044f «{card['name_ru']}» \u043d\u0435 \u043f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0430\u0435\u0442\u0441\u044f. "
                      f"\u0414\u043b\u044f \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 \u043f\u0440\u0438 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e\u0441\u0442\u0438 \u0443\u0442\u043e\u0447\u043d\u0438\u0442\u0435: {question}.")
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
