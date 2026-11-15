"""Source-linked actions and qualitative conditional paths for named candidates."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_DEMO_GUIDANCE.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "general_information_for_fictional_demo":
        raise ValueError("Guidance catalog status is invalid")
    return value


def guidance_for(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    actions, scenarios = [], []
    for candidate in candidates:
        entry = catalog()["by_candidate"].get(candidate["id"])
        if entry is None:
            continue
        for index, action in enumerate(entry["actions"], start=1):
            actions.append({
                "candidate_id": candidate["id"], "candidate_name": candidate["name"],
                **action, "kind": "conditional_general_information", "order": index,
                "category": "escalation" if candidate.get("priority") == "urgent_review" and index == 2 else "educational_information",
                "why": candidate["evidence"],
                "condition": "If complaint or deviation is current; preliminary version not confirmed.",
                "escalation": "In case of deterioration or urgent signs, activate the onboard medical responsibility person and the approved mission procedure.",
                "source_title": next((source["title"] for source in candidate["sources"] if source["url"] == action["source_url"]), urlsplit(action["source_url"]).hostname or "Source"),
                "source_scope": "General information; unconfirmed mission protocol.",
            })
        scenarios.append({
            "candidate_id": candidate["id"], "candidate_name": candidate["name"],
            "follow": entry["follow"], "ignore": entry["ignore"],
            "horizon": entry["horizon"], "source_url": entry["source_url"],
            "status": "qualitative_source_based_not_individual_prediction",
        })
    return actions, scenarios
