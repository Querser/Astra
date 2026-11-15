"""Evaluate the small, sourced catalog of named synthetic demo candidates."""

import json
from functools import lru_cache
from pathlib import Path
from statistics import mean
from typing import Any

from app.models import Observation
from app.complaint_parser import symptom_codes


EXCLUDED_FLAGS = {"invalid", "unreliable", "artifact", "stale", "conflicting"}
PROVENANCE_FLAGS = {"synthetic_ui_entry", "synthetic", "demo", "demonstration_only", "demonstrative_gradual_change", "operator_declared_urgent_demo", "imported"}


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_DEMO_DIAGNOSTIC_CANDIDATES.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("status") != "fictional_demo_only":
        raise ValueError("Diagnostic candidate catalog is not marked as a fictional demo")
    return value


def _valid(item: Observation, metric: str, unit: str, kind: str) -> bool:
    if item.metric != metric or item.unit != unit or item.value_kind != kind:
        return False
    if item.withdrawn_at is not None or item.superseded_by_id is not None:
        return False
    if EXCLUDED_FLAGS.intersection(item.quality_flags) or set(item.quality_flags) - PROVENANCE_FLAGS:
        return False
    if kind == "blood_pressure":
        return item.systolic is not None and item.diastolic is not None and 0 < item.diastolic < item.systolic
    return item.scalar_value is not None and item.scalar_value >= 0 and (metric != "spo2" or item.scalar_value <= 100)


def _ordered(observations: list[Observation], metric: str, unit: str, kind: str) -> list[Observation]:
    return sorted(
        (item for item in observations if _valid(item, metric, unit, kind)),
        key=lambda item: (item.observed_at, item.id),
    )


def _match(condition: dict[str, Any], observations: list[Observation], symptom_reports: list[dict[str, Any]]) -> tuple[list[Any], str] | None:
    rule = condition["rule"]
    rule_type = rule["type"]
    if rule_type == "repeated_low_spo2":
        recent = _ordered(observations, "spo2", rule["unit"], "scalar")[-rule["recent_observations"]:]
        if (len(recent) == rule["recent_observations"]
                and recent[-1].scalar_value <= rule["review_at_or_below"]
                and sum(item.scalar_value < rule["typical_lower_bound"] for item in recent) >= rule["minimum_below_typical"]):
            values = ", ".join(f"{item.scalar_value:g}" for item in recent)
            return recent, f"Last SpO₂: {values} %; last {recent[-1].scalar_value:g} % ≤ {rule['review_at_or_below']} %."
    elif rule_type == "repeated_high_blood_pressure":
        series = _ordered(observations, "blood_pressure", rule["unit"], "blood_pressure")
        days: dict[Any, list[Observation]] = {}
        for item in series:
            days.setdefault(item.observed_at.date(), []).append(item)
        qualifying = [day for day, items in sorted(days.items()) if len(items) >= rule["minimum_readings_per_day"]]
        if len(qualifying) >= rule["minimum_days"]:
            selected_days = qualifying[-rule["minimum_days"]:]
            recent = [item for day in selected_days for item in days[day]]
            systolic = mean(item.systolic for item in recent)
            diastolic = mean(item.diastolic for item in recent)
            if systolic >= rule["systolic_at_or_above"] or diastolic >= rule["diastolic_at_or_above"]:
                evidence = (
                    f"Over {len(selected_days)} days with {rule['minimum_readings_per_day']} or more measurements; "
                    f"mean blood pressure {systolic:.1f}/{diastolic:.1f} mmHg "
                    f"(rule threshold {rule['systolic_at_or_above']}/{rule['diastolic_at_or_above']})."
                )
                return recent, evidence
    elif rule_type == "repeated_short_sleep":
        recent = _ordered(observations, "sleep_duration", rule["unit"], "scalar")[-rule["recent_observations"]:]
        count = sum(item.scalar_value < rule["adult_recommendation_hours"] for item in recent)
        if len(recent) == rule["recent_observations"] and count >= rule["minimum_below_recommendation"]:
            values = ", ".join(f"{item.scalar_value:g}" for item in recent)
            return recent, f"Last sleep periods: {values} h; {count} of {len(recent)} shorter than {rule['adult_recommendation_hours']} h."
    elif rule_type == "symptom_cluster":
        required = set(rule["required_symptom_codes"])
        matched = [(report, set(symptom_codes(str(report.get("description", ""))))) for report in symptom_reports]
        present = set().union(*(codes for _, codes in matched)) if matched else set()
        if required <= present:
            evidence = [report for report, codes in matched if codes & required]
            return evidence, "Messages note loud snoring, observed sleep apnea and daytime sleepiness."
    elif rule_type == "head_trauma_symptom_cluster":
        # The impact and symptoms must be reported together; unrelated reports
        # from different dates cannot be combined into a trauma event.
        symptom_names = {
            "headache": "headache", "nausea": "nausea",
            "vomiting": "vomiting", "external_bleeding": "bleeding",
        }
        for report in reversed(symptom_reports):
            codes = set(symptom_codes(str(report.get("description", ""))))
            if "head_impact" not in codes:
                continue
            present = [code for code in rule["associated_symptom_codes"] if code in codes]
            if len(present) >= rule["minimum_associated_symptoms"]:
                evidence = "Reported head injury; also noted: " + ", ".join(symptom_names[code] for code in present) + "."
                if "external_bleeding" in present:
                    evidence += " The location and source of bleeding from the text are not established."
                return [report], evidence
    else:
        raise ValueError(f"Unknown diagnostic candidate rule: {rule_type}")
    return None


def evaluate_candidates(observations: list[Observation], symptom_reports: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Return named candidates only when the catalog's evidence pattern matches."""
    result = []
    for condition in catalog()["conditions"]:
        match = _match(condition, observations, symptom_reports or [])
        if match is None:
            continue
        evidence, evidence_ru = match
        result.append({
            "id": condition["id"],
            "name": condition["name_ru"],
            "kind": condition["kind"],
            "primary_metric": condition["primary_metric"],
            "status": "preliminary_demo_candidate",
            "priority": condition.get("priority", "routine_review"),
            "evidence": evidence_ru,
            "evidence_observation_ids": [item.id if isinstance(item, Observation) else str(item["id"]) for item in evidence],
            "explanation": condition["explanation_ru"],
            "missing_confirmation": condition["missing_ru"],
            "sources": [{"title": source["title"], "url": source["url"]} for source in condition["sources"]],
            "applicability": condition["applicability"],
            "catalog_version": catalog()["version"],
        })
    return sorted(result, key=lambda item: item["priority"] != "urgent_review")
