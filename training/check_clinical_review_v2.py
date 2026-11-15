"""Check completeness of an external blind review without inventing reviewer labels."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEW = ROOT / "training/data/clinical_review_blind_v2.json"
CASEBOOK = ROOT / "training/data/casebook_v2.json"
VALID_URGENCY = {"routine", "prompt_review", "emergency"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("review", nargs="?", type=Path, default=DEFAULT_REVIEW)
    args = parser.parse_args()
    source = {item["id"]: item for item in json.loads(CASEBOOK.read_text(encoding="utf-8"))["cases"]}
    rows = json.loads(args.review.read_text(encoding="utf-8"))["cases"]
    if len(rows) != len(source) or {item["id"] for item in rows} != set(source):
        raise SystemExit("Review case IDs differ from the frozen casebook")
    card_ids = {card["id"] for card in json.loads(
        (ROOT / "docs/model-led/knowledge_cards.json").read_text(encoding="utf-8"))["cards"]}
    pending, disagreements = [], []
    for row in rows:
        values = [row.get(key) for key in ("reviewer_candidate_ids", "reviewer_urgency",
                                            "reviewer_rationale", "reviewer_name", "reviewed_at")]
        if all(value is None for value in values):
            pending.append(row["id"])
            continue
        if any(value is None for value in values):
            raise SystemExit(f"Partial review entry: {row['id']}")
        if (not isinstance(values[0], list) or not set(values[0]) <= card_ids or
                values[1] not in VALID_URGENCY or not isinstance(values[2], str) or
                len(values[2].strip()) < 20 or not str(values[3]).strip()):
            raise SystemExit(f"Invalid reviewer fields: {row['id']}")
        try:
            datetime.fromisoformat(str(values[4]).replace("Z", "+00:00"))
        except ValueError as exc:
            raise SystemExit(f"Invalid reviewed_at: {row['id']}") from exc
        original = source[row["id"]]
        if set(values[0]) != set(original["expected_ids"]) or values[1] != original["urgency"]:
            disagreements.append(row["id"])
    print(json.dumps({"reviewed": len(rows) - len(pending), "total": len(rows),
                      "pending_ids": pending, "author_label_disagreements": disagreements,
                      "status": "awaiting_external_review" if pending else "review_complete_requires_adjudication"},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
