"""Build a review queue from blind model disagreements without adjudicating them."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "model-led"
cases = json.loads((PACK / "review_cases_240.json").read_text(encoding="utf-8"))["cases"]
checks = json.loads((PACK / "review_cases_240_model_check.json").read_text(encoding="utf-8"))["reviews"]
by_id = {row["id"]: row for row in checks}
assert len(cases) == len(by_id) == 240

queue = []
for case in cases:
    check = by_id[case["id"]]
    if not check["candidate_agreement"] or not check["urgency_agreement"]:
        queue.append({
            "id": case["id"],
            "messages": case["messages"],
            "author_candidate_ids": case["expected_candidate_ids"],
            "author_urgency": case["expected_urgency"],
            "author_note": case["label_note"],
            "source_urls": case["source_urls"],
            "blind_model_review": check["review"],
            "candidate_disagreement": not check["candidate_agreement"],
            "urgency_disagreement": not check["urgency_agreement"],
            "adjudication_status": "pending_independent_human_review",
        })

(PACK / "review_disagreements.json").write_text(json.dumps({
    "status": "unadjudicated_model_disagreements",
    "note": "Model disagreement is not evidence that either label is correct.",
    "total_cases": len(cases),
    "cases_with_any_disagreement": len(queue),
    "cases": queue,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Queued {len(queue)} disagreements for independent adjudication")
