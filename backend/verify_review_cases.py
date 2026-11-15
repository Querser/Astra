"""Independent structural/provenance audit of the generated case pack.

This does not attest to medical correctness or replace an external reviewer.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "model-led"
cards = json.loads((PACK / "knowledge_cards.json").read_text(encoding="utf-8"))["cards"]
cases = json.loads((PACK / "review_cases_240.json").read_text(encoding="utf-8"))["cases"]
pilot = json.loads((PACK / "eval_cases.json").read_text(encoding="utf-8"))["cases"]
by_id = {card["id"]: card for card in cards}

assert len(by_id) == len(cards)
assert len(cases) == 240
assert len({case["id"] for case in cases}) == len(cases)
assert len({" ".join(case["messages"]).casefold() for case in cases}) == len(cases)
pilot_texts = {" ".join(case["messages"]).casefold() for case in pilot}
assert not pilot_texts.intersection({" ".join(case["messages"]).casefold() for case in cases})

families = Counter(case["family"] for case in cases)
patterns = Counter((case["family"], case["pattern"]) for case in cases)
assert len(families) == 10 and all(count == 24 for count in families.values())
assert len(patterns) == 40 and all(count == 6 for count in patterns.values())

for case in cases:
    assert case["review_status"] == "author_source_check_only_external_review_pending"
    assert case["expected_urgency"] in {"routine", "prompt_review", "emergency"}
    assert case["messages"] and all(isinstance(item, str) and item.strip() for item in case["messages"])
    assert len(case["supporting_fact_spans"]) >= 1
    body = " ".join(case["messages"]).casefold()
    assert all(span.casefold() in body for span in case["supporting_fact_spans"]), case["id"]
    assert set(case["expected_candidate_ids"]).issubset(by_id), case["id"]
    assert case["source_urls"]
    for url in case["source_urls"]:
        assert urlparse(url).scheme == "https"
        assert urlparse(url).hostname in {
            "production.redcross.org", "www.nice.org.uk", "www.cdc.gov",
            "medlineplus.gov", "humanresearchroadmap.nasa.gov",
            "www.nasa.gov", "professional.heart.org",
        }, (case["id"], url)
    for card_id in case["expected_candidate_ids"]:
        assert by_id[card_id]["source"]["url"] in case["source_urls"], case["id"]

print(json.dumps({"cases": len(cases), "families": dict(sorted(families.items())),
                  "patterns": len(patterns), "unique_texts": len(cases),
                  "source_links_checked": sum(len(case["source_urls"]) for case in cases),
                  "external_clinical_review": "pending"}, ensure_ascii=False))
