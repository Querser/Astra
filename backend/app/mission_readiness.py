"""Transparent educational screening against an explicit local criteria file."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.analytics import ACTIVE_METRICS, structurally_invalid
from app.complaint_review import review_complaints
from app.diagnostic_candidates import evaluate_candidates
from app.models import CrewMember, Observation

BAD_FLAGS = {"invalid", "unreliable", "artifact", "stale", "conflicting"}


@lru_cache(maxsize=1)
def criteria_catalog() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_DEMO_MISSION_CRITERIA.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "educational_configured_screen_only":
        raise ValueError("Mission criteria scope is invalid")
    return value


def assess_mission_readiness(
    crew: CrewMember,
    observations: list[Observation],
    symptom_reports: list[dict[str, Any]],
    environment_records: list[dict[str, Any]],
) -> dict[str, Any]:
    catalog = criteria_catalog()
    active = [item for item in observations if item.metric in ACTIVE_METRICS]
    candidates = evaluate_candidates(active, symptom_reports)
    reviews, _, _ = review_complaints(symptom_reports)
    urgent = [item for item in candidates if item.get("priority") == "urgent_review"]
    other = [item for item in candidates if item.get("priority") != "urgent_review"]
    wounds = [item for item in reviews if item["status"] == "reported_visible_wound"]
    poor = [item for item in active if structurally_invalid(item) or BAD_FLAGS.intersection(item.quality_flags)]
    context_present = bool(crew.mission_location and crew.mission_phase and crew.habitat)
    outcomes = {
        "mission_context": context_present,
        "observation_present": bool(active),
        "input_quality": not poor,
        "urgent_pattern": not urgent,
        "reported_bleeding": not wounds,
        "other_candidate": not other,
    }
    factors = []
    for rule in catalog["criteria"]:
        factor: dict[str, Any] = {
            "criterion_id": rule["id"],
            "criterion": rule["description_ru"],
            "met": outcomes[rule["id"]],
        }
        if rule["id"] == "mission_context":
            factor["evidence"] = f"{crew.mission_location or 'location not specified'}; {crew.mission_phase or 'phase not specified'}; {crew.habitat or 'habitat not specified'}"
        elif rule["id"] == "observation_present":
            factor["evidence"] = f"Active current measurements: {len(active)}."
        elif rule["id"] == "input_quality":
            factor["evidence"] = f"Records with declared quality limitation: {len(poor)}."
        elif rule["id"] == "urgent_pattern":
            factor["evidence"] = "; ".join(item["name"] for item in urgent) if urgent else "Urgent version according to set rules not found."
        elif rule["id"] == "reported_bleeding":
            factor["evidence"] = "; ".join(item["description"] for item in wounds) if wounds else "Unresolved message about laceration with bleeding is not present."
        else:
            factor["evidence"] = "; ".join(item["name"] for item in other) if other else "Other versions according to set rules are not present."
        factors.append(factor)
    missing = []
    if not context_present:
        missing.append("Location, phase or residential module of mission is not fully specified.")
    if not active:
        missing.append("No applicable current measurements are present.")
    if wounds:
        missing.append("No mark about cessation of bleeding and result of wound examination is present.")
    if urgent:
        missing.append("No record about review of urgent version by responsible person is present.")
    if other:
        missing.append("No confirmation or exclusion of preliminary versions.")
    missing += [
        "Criticality of the nearest task and workload are not presented in the data model.",
        "Measurement schedule and approved limits of a specific mission are not configured.",
    ]
    if not context_present or not active:
        status = "not_assessed"
        statement = "Training readiness screen is not calculated: mission context or applicable measurements are missing."
    elif urgent:
        status = "does_not_meet_configured_criteria"
        statement = "By internal training criteria, the screen has not been passed: there is an unresolved urgent version. A person in charge needs to assess."
    elif wounds or other or poor:
        status = "conditional_review"
        statement = "By internal training criteria, a review is required: there is a complaint, preliminary version, or quality limitation."
    else:
        status = "meets_configured_criteria"
        statement = "By the presented data, internal training criteria of the screen are fulfilled; this is not a medical clearance for the mission or task."
    return {
        "crew_member_id": crew.id,
        "status": status,
        "statement": statement,
        "criteria_configured": True,
        "criteria_version": catalog["version"],
        "criteria_scope": catalog["scope_ru"],
        "contributing_factors": factors,
        "missing_data": missing,
        "mission_context": {"location": crew.mission_location, "phase": crew.mission_phase, "habitat": crew.habitat},
        "environment_record_count": len(environment_records),
        "environment_note": "Environmental measurements are shown as context, but without configured limits, they do not affect the result.",
        "required_human_follow_up": True,
    }
