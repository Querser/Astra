"""Export fictional cases without author labels, pattern names or original IDs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "model-led"
cases = json.loads((PACK / "review_cases_240.json").read_text(encoding="utf-8"))["cases"]
cards = json.loads((PACK / "knowledge_cards.json").read_text(encoding="utf-8"))["cards"]

blind = []
mapping = {}
for case in cases:
    review_id = "BR-" + hashlib.sha256(case["id"].encode("utf-8")).hexdigest()[:12].upper()
    mapping[review_id] = case["id"]
    blind.append({"review_id": review_id, "messages": case["messages"]})

assert len(set(mapping)) == len(cases)
(PACK / "review_cases_240_blind.json").write_text(json.dumps({
    "version": "0.1.0",
    "status": "awaiting_independent_review",
    "instructions": (
        "Review each fictional case without looking at the author labels or model checks. "
        "For every case provide candidate_ids, urgency, cited fact spans, source IDs, "
        "rationale, reviewer name/qualification and date. Mark unsupported or ambiguous "
        "cases for adjudication; do not guess."
    ),
    "allowed_cards": [{"id": card["id"], "name_ru": card["name_ru"],
                       "source": card["source"]} for card in cards],
    "review_fields": ["candidate_ids", "urgency", "fact_spans", "source_ids",
                      "rationale", "reviewer", "qualification", "reviewed_on", "uncertain"],
    "cases": blind,
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(PACK / "review_cases_240_blind_mapping.json").write_text(
    json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Exported {len(blind)} blinded cases")
