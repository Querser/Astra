"""Deterministic, explainable non-clinical record analysis."""

from dataclasses import dataclass
from datetime import timedelta
from statistics import median
from typing import Any

from app.models import Observation
from app.diagnostic_candidates import evaluate_candidates
from app.demo_guidance import guidance_for
from app.complaint_parser import symptom_codes
from app.complaint_review import review_complaints
from app.reference_checks import compare_reference

RULE_SET_VERSION = "2.4"
PROVENANCE_FLAGS = {
    "synthetic_ui_entry", "synthetic", "demo", "demonstration_only",
    "demonstrative_gradual_change", "operator_declared_urgent_demo", "imported",
}
ACTIVE_METRICS = (
    "heart_rate", "blood_pressure", "spo2", "body_temperature",
    "respiratory_rate", "sleep_duration", "sleep_quality", "activity",
    "exertion_fatigue",
)
SELF_REPORTED_METRICS = {"sleep_duration", "sleep_quality", "exertion_fatigue"}
DISPLAY_UNITS = {"bpm": "beats/min", "breaths/min": "breaths/min", "h": "h", "steps": "steps", "score": "points", "mmHg": "mmHg"}


def _ru_number(value: float | int) -> str:
    return f"{value:g}"


def _ru_score(value: float | int) -> str:
    if value != int(value):
        return "points"
    number = abs(int(value))
    if 11 <= number % 100 <= 14:
        return "points"
    return "point" if number % 10 == 1 else "points" if 2 <= number % 10 <= 4 else "points"


def structurally_invalid(item: Observation) -> bool:
    """Reject impossible numeric domains, not clinical outlier thresholds."""

    if item.value_kind == "blood_pressure":
        return item.systolic is None or item.diastolic is None or item.systolic <= 0 or item.diastolic <= 0
    value = item.scalar_value
    if value is None:
        return True
    if item.metric == "spo2":
        return value < 0 or value > 100
    if item.metric in {"heart_rate", "respiratory_rate"}:
        return value <= 0
    if item.metric in {"sleep_duration", "sleep_quality", "activity", "exertion_fatigue"}:
        return value < 0
    return False


@dataclass(frozen=True)
class AnalysisPlan:
    input_ids: list[str]
    facts: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    guidance: list[dict[str, Any]]
    hypotheses: list[dict[str, Any]]
    unknowns: list[dict[str, Any]]
    alerts: list[dict[str, str]]


def analyze_observations(
    observations: list[Observation],
    *,
    source_types: dict[str, str] | None = None,
    symptom_reports: list[dict[str, Any]] | None = None,
    environment_records: list[dict[str, Any]] | None = None,
    mission_context: dict[str, Any] | None = None,
) -> AnalysisPlan:
    """Report observations, sourced comparisons and named demo candidates."""

    # Historic laboratory records remain stored, but are not an active input.
    observations = [item for item in observations if item.metric in ACTIVE_METRICS]
    source_types = source_types or {}
    symptom_reports = symptom_reports or []
    environment_records = environment_records or []
    facts: list[dict[str, Any]] = [
        {
            "kind": "observation_count",
            "value": len(observations),
            "statement": f"{len(observations)} current observations were evaluated.",
        }
    ]
    findings: list[dict[str, Any]] = []
    alerts: list[dict[str, str]] = []
    guidance: list[dict[str, Any]] = []
    hypotheses: list[dict[str, Any]] = []
    by_metric: dict[str, list[Observation]] = {}
    latest_by_metric: dict[str, Observation] = {}
    quality_counts: dict[str, int] = {}
    for observation in observations:
        by_metric.setdefault(observation.metric, []).append(observation)
        for flag in set(observation.quality_flags) - PROVENANCE_FLAGS:
            quality_counts[flag] = quality_counts.get(flag, 0) + 1

    for flag, count in sorted(quality_counts.items()):
        findings.append(
            {
                "rule_id": "quality_flags_present",
                "quality_flag": flag,
                "affected_observations": count,
                "statement": f"{count} observation(s) carry the declared quality flag: {flag}.",
                "clinical_significance": "not_established",
            }
        )
        alerts.append(
            {
                "rule_id": "quality_flags_present",
                "title": "Data quality review",
                "explanation": f"{count} record(s) carry the declared quality flag '{flag}'. Review collection conditions; clinical significance is not established.",
            }
        )

    metrics_with_repeat = 0
    for metric, series in by_metric.items():
        ordered = sorted(series, key=lambda item: (item.observed_at, item.id))
        latest_observation = ordered[-1]
        latest_by_metric[metric] = latest_observation
        units = {item.unit for item in ordered}
        same_unit = len(units) == 1
        if len(ordered) > 1:
            metrics_with_repeat += 1
        scalar_series = [
            item for item in ordered
            if item.value_kind == "scalar" and item.scalar_value is not None
        ]
        snapshot: dict[str, Any] = {
            "kind": "metric_snapshot",
            "metric": metric,
            "count": len(ordered),
            "latest_observation_id": latest_observation.id,
            "latest_observed_at": latest_observation.observed_at.isoformat() + "Z",
            "latest_value": latest_observation.value,
            "unit": latest_observation.unit,
            "synthetic_count": sum(item.synthetic for item in ordered),
            "comparison_status": "mixed_units" if not same_unit else "single_point" if len(ordered) == 1 else "repeated",
        }
        if same_unit and len(scalar_series) == len(ordered):
            values = [item.scalar_value for item in scalar_series]
            snapshot["minimum"] = min(values)
            snapshot["maximum"] = max(values)
            snapshot["median"] = median(values)
            if len(values) >= 2:
                snapshot["delta_from_previous"] = round(values[-1] - values[-2], 6)
        facts.append(snapshot)

        reference = compare_reference(latest_observation)
        if structurally_invalid(latest_observation) or set(latest_observation.quality_flags) & {"invalid", "unreliable", "artifact", "stale", "conflicting"} or not same_unit:
            reference = {**reference, "status": "not_assessed", "reason": "invalid_stale_or_conflicting_input"}
        facts.append(reference)
        if reference["status"] in {"below_reference", "above_reference"}:
            findings.append(
                {
                    "rule_id": "reference_comparison",
                    "metric": metric,
                    "observation_id": latest_observation.id,
                    "status": reference["status"],
                    "value": reference["value"],
                    "unit": reference["reference_unit"],
                    "reference_low": reference["reference_low"],
                    "reference_high": reference["reference_high"],
                    "context": reference["context"],
                    "source_title": reference["source_title"],
                    "source_url": reference["source_url"],
                    "statement": "Latest value is outside a conditional public adult reference point.",
                    "clinical_significance": "requires_context_and_confirmation",
                }
            )
            alerts.append(
                {
                    "rule_id": "reference_comparison",
                    "title": "Reference comparison review",
                    "explanation": "Latest value differs from a public adult reference point. Confirm context and measurement; this does not identify a disease.",
                }
            )
            if metric == "spo2" and reference["status"] == "below_reference":
                guidance.append(
                    {
                        "kind": "verify_oxygen_reading",
                        "metric": metric,
                        "statement": "For a real concerning reading or symptoms, contact the responsible mission medical professional; checking the sensor must not delay that review. Verify the device and repeat the reading when appropriate.",
                        "source_title": "FDA: Pulse Oximeter Basics",
                        "source_url": "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics",
                    }
                )
                hypotheses.append(
                    {
                        "kind": "possible_low_oxygen",
                        "statement": "A confirmed low oxygen reading could indicate low blood oxygen; this single unverified entry cannot establish the cause or a diagnosis.",
                        "evidence_observation_ids": [latest_observation.id],
                        "source_title": "FDA: Pulse Oximeter Basics",
                        "source_url": "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics",
                    }
                )
            elif metric in {"heart_rate", "respiratory_rate"}:
                guidance.append(
                    {
                        "kind": "verify_resting_context",
                        "metric": metric,
                        "statement": "Check the entered unit and whether the measurement was taken at rest. A persistent or symptomatic deviation needs qualified review.",
                        "source_title": reference["source_title"],
                        "source_url": reference["source_url"],
                    }
                )
            elif metric == "sleep_duration" and reference["status"] == "below_reference":
                guidance.append(
                    {
                        "kind": "sleep_habits",
                        "metric": metric,
                        "statement": "Review the sleep schedule and quality; CDC lists regular timing and a quiet, cool bedroom among sleep habits.",
                        "source_title": reference["source_title"],
                        "source_url": reference["source_url"],
                    }
                )

        if not same_unit:
            findings.append(
                {
                    "rule_id": "unit_mismatch",
                    "metric": metric,
                    "units": sorted(units),
                    "statement": "This metric has records with different units; numerical comparison was skipped.",
                    "clinical_significance": "not_established",
                }
            )
            alerts.append(
                {
                    "rule_id": "unit_mismatch",
                    "title": "Unit consistency review",
                    "explanation": "Measurements of this metric use different units. Reconcile units before comparing values.",
                }
            )
            continue
        if len(scalar_series) < 6 or structurally_invalid(latest_observation) or set(latest_observation.quality_flags) & {"invalid", "unreliable", "artifact", "stale", "conflicting"}:
            continue
        historical = [item.scalar_value for item in scalar_series[:-1] if item.scalar_value is not None]
        latest = scalar_series[-1]
        center = median(historical)
        deviations = [abs(value - center) for value in historical]
        mad = median(deviations)
        if mad == 0:
            continue
        score = 0.6745 * ((latest.scalar_value or 0.0) - center) / mad
        if abs(score) > 3.5:
            findings.append(
                {
                    "rule_id": "descriptive_series_change",
                    "observation_id": latest.id,
                    "metric": metric,
                    "statement": "Latest value differs from its earlier local series under a robust descriptive statistic.",
                    "baseline_median": center,
                    "modified_z_score": round(score, 3),
                    "clinical_significance": "not_established",
                }
            )
            alerts.append(
                {
                    "rule_id": "descriptive_series_change",
                    "title": "Descriptive series review",
                    "explanation": "A within-series descriptive change was detected. This is not a diagnosis or clinical risk estimate.",
                }
            )

    oxygen = latest_by_metric.get("spo2")
    breathing = latest_by_metric.get("respiratory_rate")
    if oxygen is not None and breathing is not None and not any(
        structurally_invalid(item) or set(item.quality_flags) & {"invalid", "unreliable", "artifact", "stale", "conflicting"}
        for item in (oxygen, breathing)
    ):
        oxygen_review = compare_reference(oxygen)
        breathing_review = compare_reference(breathing)
        if (
            oxygen_review["status"] == "below_reference"
            and breathing_review["status"] == "above_reference"
            and abs(oxygen.observed_at - breathing.observed_at) <= timedelta(minutes=30)
        ):
            findings.append(
                {
                    "rule_id": "coincident_oxygen_breathing",
                    "observation_ids": [oxygen.id, breathing.id],
                    "statement": "Low oxygen and high breathing-rate readings were recorded within 30 minutes; coincidence does not establish a cause.",
                    "source_title": "FDA: Pulse Oximeter Basics",
                    "source_url": "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics",
                    "clinical_significance": "requires_context_and_confirmation",
                }
            )

    facts.append(
        {
            "kind": "series_coverage",
            "metric_count": len(by_metric),
            "metrics_with_repeat": metrics_with_repeat,
            "metrics_without_repeat": len(by_metric) - metrics_with_repeat,
            "statement": "Repeated observations are required for within-person change analysis.",
        }
    )
    unknowns = [
        {
            "kind": "mission_reference",
            "statement": "Public terrestrial adult reference points are conditional and are not validated mission-specific limits; named demo candidates require confirmation before a clinical conclusion.",
        },
        {
            "kind": "collection_schedule",
            "statement": "No expected measurement schedule is configured, so missingness and staleness cannot be inferred clinically.",
        },
    ]
    if by_metric and metrics_with_repeat < len(by_metric):
        unknowns.append(
            {
                "kind": "personal_history",
                "metric_count": len(by_metric) - metrics_with_repeat,
                "statement": "Some metrics have only one observation, so within-person change cannot be assessed for them.",
            }
        )
    if any(item["rule_id"] == "reference_comparison" for item in findings):
        unknowns.append(
            {
                "kind": "measurement_context",
                "statement": "Rest/activity state, symptoms, device details and cabin conditions were not recorded, so causes and severity cannot be determined from these entries alone.",
            }
        )
    diagnostic_candidates = evaluate_candidates(observations, symptom_reports)
    for candidate in diagnostic_candidates:
        if candidate.get("priority") == "urgent_review":
            findings.append({
                "rule_id": "urgent_head_injury_pattern",
                "statement": candidate["evidence"],
                "evidence_observation_ids": candidate["evidence_observation_ids"],
                "clinical_significance": "urgent_review",
                "source_url": candidate["sources"][0]["url"],
                "source_title": candidate["sources"][0]["title"],
            })
            alerts.append({
                "rule_id": "urgent_head_injury_pattern",
                "title": "Possible head injury: urgent assessment",
                "explanation": candidate["evidence"] + "In-person medical assessment is needed if the injury is recent.",
            })
    parameter_assessments = _parameter_assessments(by_metric, source_types, diagnostic_candidates, mission_context)
    all_input_ids = [item.id for item in observations]
    all_input_ids += [str(item["id"]) for item in symptom_reports if item.get("id")]
    all_input_ids += [str(item["id"]) for item in environment_records if item.get("id")]
    integrated_report = _integrated_report(
        parameter_assessments, findings, guidance, hypotheses, unknowns,
        symptom_reports, environment_records, all_input_ids, diagnostic_candidates, mission_context,
    )
    facts.extend({"kind": "parameter_assessment", **item} for item in parameter_assessments)
    facts.append({"kind": "integrated_report", **integrated_report})
    return AnalysisPlan(
        input_ids=all_input_ids,
        facts=facts,
        findings=findings,
        guidance=guidance,
        hypotheses=hypotheses,
        unknowns=unknowns,
        alerts=alerts,
    )


def _parameter_assessments(
    by_metric: dict[str, list[Observation]], source_types: dict[str, str],
    diagnostic_candidates: list[dict[str, Any]], mission_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for metric, series in sorted(by_metric.items()):
        ordered = sorted(series, key=lambda item: (item.observed_at, item.id))
        latest = ordered[-1]
        collection = latest.measurement_context or {}
        entry_kind = source_types.get(latest.source_id, "unknown")
        flags = set(latest.quality_flags)
        declared_flags = sorted(flags - PROVENANCE_FLAGS)
        mixed_units = len({item.unit for item in ordered}) > 1 or "conflicting" in flags
        invalid = structurally_invalid(latest) or bool(flags & {"invalid", "unreliable", "artifact"})
        stale = "stale" in flags
        quality_status = (
            "declared_invalid" if invalid else "conflicting_units" if mixed_units
            else "declared_stale" if stale else "flagged" if declared_flags else "unflagged"
        )
        freshness_status = "declared_stale" if stale else "not_assessed_no_schedule"
        availability_class = (
            "synthetic" if latest.synthetic else "self_reported" if metric in SELF_REPORTED_METRICS
            else "measured" if entry_kind == "sensor" else "manually_entered"
            if entry_kind == "manual" else "unknown"
        )
        # A manually transcribed instrument value does not identify its device.
        acquisition_kind = (
            "self_report" if collection.get("subjective") is True or metric in SELF_REPORTED_METRICS
            else "device" if collection.get("device") or entry_kind == "sensor" else "unknown"
        )
        reference = compare_reference(latest)
        display_unit = DISPLAY_UNITS.get(latest.unit, latest.unit)
        candidate = next((item for item in diagnostic_candidates if item["primary_metric"] == metric), None)
        if invalid or mixed_units or stale:
            reference = {**reference, "status": "not_assessed", "reason": "invalid_stale_or_conflicting_input"}
        reference_view = {
            "status": reference["status"],
            "reason": reference.get("reason"),
            "applicability": "unverified" if reference.get("source_url") else "unavailable",
            "scope": "terrestrial_general_adult" if reference.get("source_url") else "none",
            "low": reference.get("reference_low"),
            "high": reference.get("reference_high"),
            "unit": reference.get("reference_unit"),
            "source_title": reference.get("source_title"),
            "source_url": reference.get("source_url"),
            "context": reference.get("context"),
            "population": reference.get("population"),
            "measurement_method": reference.get("measurement_method"),
            "source_date": reference.get("source_date"),
            "limitations": reference.get("limitations"),
            "description_ru": reference.get("description_ru"),
        }
        scalar = all(item.value_kind == "scalar" and item.scalar_value is not None for item in ordered)
        personal_series: dict[str, Any] = {
            "status": "insufficient_history", "count": len(ordered), "approved": False,
            "baseline_available": False,
            "limitation": "Only an unapproved descriptive series is available; no verified personal baseline is stored.",
        }
        if mixed_units:
            personal_series["status"] = "conflicting_units"
        elif invalid:
            personal_series["status"] = "invalid_latest"
        elif metric == "blood_pressure" and len(ordered) >= 2 and all(item.value_kind == "blood_pressure" for item in ordered):
            personal_series["status"] = "descriptive_only"
            personal_series["systolic_delta_from_previous"] = round(float(latest.systolic) - float(ordered[-2].systolic), 3)
            personal_series["diastolic_delta_from_previous"] = round(float(latest.diastolic) - float(ordered[-2].diastolic), 3)
        elif scalar and len(ordered) >= 2:
            previous = ordered[-2].scalar_value
            personal_series["status"] = "descriptive_only"
            personal_series["delta_from_previous"] = round(float(latest.scalar_value) - float(previous), 6)
            if len(ordered) >= 6:
                history = [float(item.scalar_value) for item in ordered[:-1]]
                center = median(history)
                mad = median(abs(value - center) for value in history)
                personal_series["historical_median"] = center
                personal_series["historical_mad"] = mad
                if mad > 0:
                    score = 0.6745 * (float(latest.scalar_value) - center) / mad
                    personal_series["status"] = "descriptive_change" if abs(score) > 3.5 else "descriptive_only"
                    personal_series["modified_z_score"] = round(score, 3)
        insight: dict[str, Any] = {"count": len(ordered), "summary": "A repeat comparable history is needed for direction changes."}
        if scalar and len(ordered) >= 4 and not mixed_units and not invalid:
            values = [float(item.scalar_value) for item in ordered]
            recent = values[-min(7, len(values)):]
            old = values[:min(3, len(values) - 3)]
            recent_center = median(recent[-3:])
            old_center = median(old)
            delta = recent_center - old_center
            delta_unit = _ru_score(abs(delta)) if metric in {"sleep_quality", "exertion_fatigue"} else display_unit.rstrip(".")
            direction = f"increased by {_ru_number(abs(delta))} {delta_unit}" if delta > 0 else f"decreased by {_ru_number(abs(delta))} {delta_unit}" if delta < 0 else "no change"
            series_unit = display_unit.rstrip(".")
            movement = f"indicator {direction}" if delta else "indicator no change"
            first_unit = _ru_score(old_center) if metric in {"sleep_quality", "exertion_fatigue"} else series_unit
            recent_unit = _ru_score(recent_center) if metric in {"sleep_quality", "exertion_fatigue"} else series_unit
            range_unit = _ru_score(max(recent)) if metric in {"sleep_quality", "exertion_fatigue"} else series_unit
            insight = {
                "count": len(values), "first_median": round(old_center, 2),
                "recent_median": round(recent_center, 2), "delta": round(delta, 2),
                "recent_min": min(recent), "recent_max": max(recent),
                "summary": f"Series of {len(values)} points: median of first {len(old)} — {_ru_number(old_center)} {first_unit}, last 3 — {_ru_number(recent_center)} {recent_unit}; {movement}. Last {len(recent)}: {_ru_number(min(recent))}–{_ru_number(max(recent))} {range_unit}.",
            }
            if metric == "spo2" and len(values) >= 8 and values[-8] < 95 and all(value >= 95 for value in values[-7:]):
                insight["pattern"] = "isolated_low_followed_by_seven_typical"
                insight["summary"] += f"An isolated low value {_ru_number(values[-8])} % has been replaced by seven values {_ru_number(min(values[-7:]))}–{_ru_number(max(values[-7:]))} %: there is no sustained decline in the last points."
            if metric in {"sleep_quality", "exertion_fatigue"}:
                insight["summary"] += "This is an internal self-assessment 0–10: for sleep quality, higher means better; for fatigue, higher means worse; there is no clinical threshold for the scale."
            if metric == "activity":
                insight["summary"] += "Steps show personal dynamics; they cannot be used to determine minutes of moderate activity."
                insight["context_note"] = "CDC recommends adults 150 minutes of moderate activity per week and two days of strength exercises. This benchmark cannot be checked by the number of steps."
                insight["source_url"] = "https://www.cdc.gov/physical-activity-basics/guidelines/adults.html"
            elif metric == "sleep_quality":
                insight["context_note"] = "CDC describes quality sleep as continuous and restorative; ASTRA scores remain subjective."
                insight["source_url"] = "https://www.cdc.gov/sleep/about/index.html"
            elif metric == "exertion_fatigue":
                insight["context_note"] = "Subjective fatigue assessment should be considered together with physiological indicators; there is no universal threshold for the ASTRA scale."
                insight["source_url"] = "https://www.nasa.gov/human-systems-integration-division/psychophysiology-research-laboratory/"
        if candidate:
            status = "diagnostic_candidate"
            explanation = f"{candidate['name']}: {candidate['evidence']}"
        elif reference["status"] in {"bp_stage2_range", "bp_stage1_range", "bp_elevated_range"}:
            status = "outside_available_reference"
            explanation = f"Blood pressure {_ru_number(latest.systolic)}/{_ru_number(latest.diastolic)} {display_unit} falls into {reference['description_ru']} according to the earth classification for adults. One record does not confirm the diagnosis."
        elif reference["status"] == "bp_normal_range":
            status = "within_available_reference"
            explanation = f"Blood pressure {_ru_number(latest.systolic)}/{_ru_number(latest.diastolic)} {display_unit} falls into the published category of normal blood pressure for adults."
        elif invalid:
            status = "invalid"
            explanation = "The quality of the last record is declared unreliable; numerical conclusion is not performed."
        elif mixed_units:
            status = "conflicting"
            explanation = "Records have different units or declared conflict; personal numerical comparison is impossible."
        elif stale:
            status = "stale"
            explanation = "Record marked as outdated by the source; current status cannot be determined based on it."
        elif reference["status"] in {"below_reference", "above_reference"}:
            status = "outside_available_reference"
            direction = "below" if reference["status"] == "below_reference" else "above"
            explanation = f"The last value {_ru_number(latest.scalar_value)} {display_unit} {direction} reaches the published reference marker {reference.get('reference_low')}–{reference.get('reference_high') or '∞'} {DISPLAY_UNITS.get(reference.get('reference_unit'), reference.get('reference_unit'))}."
        elif reference["status"] == "at_or_above_fever_threshold":
            status = "outside_available_reference"
            explanation = f"Temperature {_ru_number(latest.scalar_value)} °C reaches the published reference marker for high temperature 38 °C in adults. Clarify the method of measurement and symptoms."
        elif reference["status"] == "below_fever_threshold":
            status = "within_available_reference"
            explanation = f"Temperature {_ru_number(latest.scalar_value)} °C is below the adult fever threshold of 38 °C; this does not exclude illness."
        elif personal_series["status"] == "descriptive_change":
            status = "changed_from_personal_series"
            explanation = "An observational change in the series is noted; there is no established personal norm."
        elif reference["status"] in {"within_reference", "meets_minimum"}:
            status = "within_available_reference"
            explanation = f"The last value {_ru_number(latest.scalar_value)} {display_unit} falls within the published reference range for the specified population."
        elif personal_series["status"] == "descriptive_only":
            status = "descriptive_trend"
            display = f"{_ru_number(latest.scalar_value)} {_ru_score(latest.scalar_value) if metric in {'sleep_quality', 'exertion_fatigue'} else display_unit}" if latest.value_kind == "scalar" else f"{_ru_number(latest.systolic)}/{_ru_number(latest.diastolic)} {display_unit}"
            explanation = f"The last value {display}; direction and spread are shown based on personal history below."
        else:
            status = "insufficient_evidence"
            explanation = "There is no applicable validated comparison for this indicator; the initial value is retained."
        missing_context = ["approved_personal_baseline"]
        if not collection.get("method"):
            missing_context.append("measurement_method")
        if mission_context is None and not collection.get("mission_phase"):
            missing_context.append("mission_phase")
        if candidate:
            missing_context = [item for item in missing_context if item != "approved_personal_baseline"]
        if metric in {"heart_rate", "respiratory_rate"} and not collection.get("activity_state"):
            missing_context.append("rest_or_activity_state")
        if metric == "spo2" and not collection.get("device"):
            missing_context.append("device_and_signal_quality")
        result.append({
            "metric": metric,
            "observation_id": latest.id,
            "value": latest.value,
            "unit": latest.unit,
            "observed_at": latest.observed_at.isoformat() + "Z",
            "recorded_at": latest.recorded_at.isoformat() + "Z",
            "source_id": latest.source_id,
            "measurement_context": latest.measurement_context,
            "entry_kind": entry_kind,
            "acquisition_kind": acquisition_kind,
            "availability_class": availability_class,
            "synthetic": latest.synthetic,
            "quality_flags": sorted(flags),
            "quality_status": quality_status,
            "freshness_status": freshness_status,
            "reference": reference_view,
            "personal_series": personal_series,
            "series_insight": insight,
            "status": status,
            "explanation": explanation,
            "diagnostic_candidate_id": candidate["id"] if candidate else None,
            "missing_context": missing_context,
        })
    return result


def _integrated_report(
    assessments: list[dict[str, Any]],
    findings: list[dict[str, Any]],
    guidance: list[dict[str, Any]],
    hypotheses: list[dict[str, Any]],
    unknowns: list[dict[str, Any]],
    symptom_reports: list[dict[str, Any]],
    environment_records: list[dict[str, Any]],
    input_ids: list[str],
    diagnostic_candidates: list[dict[str, Any]],
    mission_context: dict[str, Any] | None,
) -> dict[str, Any]:
    finding_text = {
        "quality_flags_present": "There are declared quality flags in the records; clinical significance is not established.",
        "reference_comparison": "The value differs from the conditional Earth reference; applicability to the mission is not confirmed.",
        "unit_mismatch": "Units of measurement for the series vary; numerical comparison is missing.",
        "descriptive_series_change": "A descriptive change was found in the personal series; this is not a diagnosis.",
        "coincident_oxygen_breathing": "SpO₂ readings and respiratory rate are close in time; the cause of the coincidence is not established.",
        "urgent_head_injury_pattern": "After the reported head strike, there are signs of possible injury; urgent in-person evaluation is required.",
    }
    guidance_text = {
        "verify_oxygen_reading": "If the actual reading causes concern or there are symptoms, contact the mission's responsible medical officer; sensor check should not delay the report. If possible, clarify the measurement.",
        "verify_resting_context": "Clarify the unit, method, and resting state during measurement. Repeated deviation or symptoms require specialist evaluation.",
        "sleep_habits": "Check the graph and sleep quality; this is general Earth information, not a guarantee of results in flight.",
    }
    unknown_text = {
        "mission_reference": "Earth references are not established limits for a space mission.",
        "collection_schedule": "The measurement graph is not defined; gaps and clinical relevance cannot be assessed.",
        "personal_history": "For some indicators, there is no repeat comparable history.",
        "measurement_context": "All measurement conditions, device, and mission phase are not recorded; the cause of deviation is unknown.",
    }
    reference_sources = sorted({
        item["reference"]["source_url"] for item in assessments
        if item["reference"].get("source_url")
    } | {source["url"] for candidate in diagnostic_candidates for source in candidate["sources"]})
    candidate_actions, condition_scenarios = guidance_for(diagnostic_candidates)
    complaint_review, wound_actions, wound_scenario = review_complaints(symptom_reports)
    oxygen_recovery = next((item for item in assessments if item["metric"] == "spo2" and item["series_insight"].get("pattern") == "isolated_low_followed_by_seven_typical"), None)
    oxygen_scenario = {
        "status": "descriptive_follow_up_scenario",
        "initial_event": oxygen_recovery["series_insight"]["summary"] if oxygen_recovery else "",
        "time_horizon": "following comparable measurements",
        "follow_recommendations": "Checking the device, conditions, and following measurements will help distinguish between a single failure and recurring reduction; this does not imply improvement in health.",
        "ignore_recommendations": "Without new measurements and information about symptoms, it is unknown whether the low value will recur.",
        "uncertainty": "The cause of the reading 91 % is not established; the following seven values 97–99 % do not prove the absence of any disease.",
        "source_title": "FDA: Pulse Oximeter Basics",
        "source_url": "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics",
    } if oxygen_recovery and not diagnostic_candidates else None
    reference_sources = sorted(set(reference_sources) | {
        source["url"] for step in wound_actions for source in step.get("sources", [])
    } | {step["source_url"] for step in candidate_actions if step.get("source_url")})
    urgent_candidates = [item for item in diagnostic_candidates if item.get("priority") == "urgent_review"]
    if urgent_candidates:
        primary = urgent_candidates[0]
        overall_assessment = f"Please urgently clarify the relevance of the complaint: {primary['name']}. {primary['evidence']} If symptoms persist, perform actions from the recommendations section."
        others = [item["name"] for item in diagnostic_candidates if item is not primary]
        if others:
            overall_assessment += " Other versions: " + "; ".join(others) + "."
    elif diagnostic_candidates:
        overall_assessment = (
            "Preliminary diagnostic versions were identified based on the entered complaints and measurements: "
            + "; ".join(item["name"] for item in diagnostic_candidates)
            + "Specific values and necessary checks are provided below."
        )
    elif assessments and all(item["status"] in {"within_available_reference", "descriptive_trend"} for item in assessments):
        overall_assessment = (
            f"The educational profile appears stable: according to {sum(item['personal_series']['count'] for item in assessments)} "
            "measurements, no significant deviations according to the set rules have been identified. "
            "Within this knowledge base, there are no diagnostic versions."
        )
    elif assessments:
        overall_assessment = (
            "There are deviations in measurements, but none of them so far correspond to the rule "
            "of the named diagnostic version in the current knowledge base. See the values for the indicators."
        )
    else:
        overall_assessment = "No measurements have been received; it is not possible to perform a numerical assessment of the indicators. Complaints are considered separately."
    if wound_actions:
        overall_assessment += " In the complaint, there is also a report of a cut with bleeding: a check of the wound condition and conditional first aid steps below are needed; the severity and source of the bleeding by blood color are not determined."
    # Parameter values already appear in parameter_assessments. Repeating them here
    # made the report longer without adding evidence.
    observed_facts = []
    if symptom_reports:
        observed_facts.append({
            "statement": f"Messages about symptoms have been received: {len(symptom_reports)}.",
            "observation_ids": [str(item["id"]) for item in symptom_reports],
            "status": "self_reported",
        })
        symptom_names = {
            "loud_snoring": "loud snoring", "witnessed_breathing_pauses": "observed sleep apnea",
            "daytime_sleepiness": "daytime sleepiness", "headache": "headache",
            "head_impact": "head impact", "nausea": "nausea", "vomiting": "vomiting",
            "external_bleeding": "bleeding (location not specified)",
            "dyspnea": "difficult breathing", "chest_pain": "chest pain", "vision_change": "visual changes",
        }
        recognized = sorted({code for report in symptom_reports for code in symptom_codes(str(report.get("description", "")))})
        if recognized:
            observed_facts.append({
                "statement": "Recognized complaints: " + ", ".join(symptom_names.get(code, code) for code in recognized) + ".",
                "observation_ids": [str(item["id"]) for item in symptom_reports if item.get("id")],
                "status": "reported_symptom_codes",
            })
    deterministic_findings = []
    deterministic_findings.extend({
        "statement": finding_text.get(item.get("rule_id"), "Calculated finding requires context verification."),
        "status": item.get("rule_id", "finding"),
        "source_url": item.get("source_url"),
        "source_title": item.get("source_title"),
    } for item in findings if item.get("statement") and item.get("rule_id") in {"coincident_oxygen_breathing", "urgent_head_injury_pattern"})
    possible_explanations = [
        {
            "statement": "Confirmed low SpO₂ may indicate reduced oxygen saturation; one unverified reading does not establish the cause or diagnosis." if item.get("kind") == "possible_low_oxygen" else "Possible explanation requires human verification; diagnosis not established.",
            "status": "requires_human_review",
            "observation_ids": item.get("evidence_observation_ids", []),
            "missing_evidence": ["repeat_measurement", "measurement_method", "clinical_context"],
            "not_a_diagnosis": True,
            "source_url": item.get("source_url"),
            "source_title": item.get("source_title"),
        }
        for item in hypotheses if item.get("source_url")
    ]
    next_steps = wound_actions + candidate_actions + [
        {
            "statement": guidance_text.get(item.get("kind"), "Clarify the data and discuss the result with the responsible specialist."),
            "kind": "general_information" if item.get("kind") == "sleep_habits" else "contact_medical_officer" if item.get("kind") == "verify_oxygen_reading" else "collect_more_data",
            "source_url": item.get("source_url"),
            "source_title": item.get("source_title"),
            "context": "conditional_terrestrial_reference; mission protocol takes precedence",
        }
        for item in guidance if item.get("source_url") and not diagnostic_candidates
    ]
    if not diagnostic_candidates and any(item["metric"] == "blood_pressure" and item["reference"]["status"] in {"bp_stage1_range", "bp_stage2_range"} for item in assessments):
        next_steps.insert(0, {
            "statement": "The last pressure fell into the elevated category. Repeat the cuff measurement after 5 minutes of rest and record both numbers; one record cannot be considered a diagnosis.",
            "kind": "repeat_blood_pressure",
            "source_title": "AHA: Home Blood Pressure Monitoring",
            "source_url": "https://www.heart.org/en/health-topics/high-blood-pressure/understanding-blood-pressure-readings/monitoring-your-blood-pressure-at-home",
        })
    if not next_steps and assessments:
        next_steps.append({
            "statement": "For a more reliable comparison, record the method, measurement conditions, and mission phase.",
            "kind": "collect_more_data",
            "source_title": f"ASTRA data-quality rule {RULE_SET_VERSION}",
            "source_url": None,
            "context": "No clinical interpretation is made from missing context.",
        })
    environmental_context = {
        **(mission_context or {}),
        "status": "profile_context" if mission_context else "profile_environment_only" if environment_records else "not_available",
        "records": environment_records,
        "statement": (
            f"{mission_context['name']}; phase: {mission_context['phase']}; residential module: {mission_context['habitat']}. "
            f"{mission_context['gravity']}. External environment: {mission_context['external_atmosphere']}. "
            f"Radiation: {mission_context['radiation']}. "
            f"Number of environmental measurements for this profile: {len(environment_records)}."
            "General information about the location is not personal exposure."
            if mission_context else f"Mission location and phase are not recorded; environmental measurements linked to this profile: {len(environment_records)}."
        ),
    }
    return {
        "coverage": {
            "observation_count": sum(item["personal_series"]["count"] for item in assessments),
            "parameter_count": len(assessments),
            "not_recorded_metrics": sorted(set(ACTIVE_METRICS) - {item["metric"] for item in assessments}),
            "symptom_report_count": len(symptom_reports),
            "synthetic_parameter_count": sum(bool(item["synthetic"]) for item in assessments),
            "freshness_policy": "no_expected_schedule_configured",
        },
        "observed_facts": observed_facts,
        "complaint_review": complaint_review,
        "overall_assessment": overall_assessment,
        "diagnostic_candidates": diagnostic_candidates,
        "deterministic_findings": deterministic_findings,
        "possible_explanations": possible_explanations,
        "unverified_hypotheses": [],
        "mission_environment_context": environmental_context,
        "next_steps": next_steps,
        "condition_scenarios": condition_scenarios,
        "scenario_comparison": wound_scenario or oxygen_scenario or {
            "status": "unsupported_without_evaluated_causal_model",
            "assumptions": ["No validated intervention-effect model is available."],
            "time_horizon": "not_established",
            "follow_recommendations": "Individual result is unknown; you can repeat the measurement and discuss it with a specialist.",
            "ignore_recommendations": "Individual result is also unknown; numerical prediction is not constructed.",
            "uncertainty": "These options are not medical predictions and do not guarantee a change in condition.",
        },
        "uncertainty": [
            {"statement": unknown_text.get(item.get("kind"), "Interpretation is limited by available data."), "kind": item.get("kind", "unknown")}
            for item in unknowns
        ] + [
            {"statement": "Absence of record does not mean absence of symptom or problem.", "kind": "missing_data"}
        ],
        "provenance": {
            "rule_set_version": RULE_SET_VERSION,
            "input_ids": input_ids,
            "reference_source_urls": reference_sources,
            "knowledge_package_status": "demo_diagnostic_catalog_active",
            "local_llm_role": "optional_explanation_only",
        },
    }
