"""Source-linked, conditional reference comparisons for the fictional demo.

These are public adult reference points, not mission medical limits. The
source pages are linked, not copied into training data or embedded as prose.
"""

from dataclasses import dataclass
from typing import Any

from app.models import Observation


@dataclass(frozen=True)
class ReferenceSpec:
    unit: str
    lower: float
    upper: float | None
    context: str
    source_title: str
    source_url: str
    population: str
    measurement_method: str
    source_date: str | None
    limitations: str


REFERENCES: dict[str, ReferenceSpec] = {
    "heart_rate": ReferenceSpec(
        "bpm", 60, 100, "adult_at_rest",
        "NIH NHLBI: How the Heart Beats",
        "https://www.nhlbi.nih.gov/health/heart/heart-beats",
        "general adults at rest", "resting pulse; ASTRA method unrecorded", None,
        "Not an individual or microgravity reference.",
    ),
    "spo2": ReferenceSpec(
        "%", 95, 100, "most_healthy_people; conditions_not_recorded",
        "FDA: Pulse Oximeter Basics",
        "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics",
        "most healthy individuals", "pulse oximetry; ASTRA device unrecorded", None,
        "Device and collection conditions can affect accuracy; not a mission limit.",
    ),
    "respiratory_rate": ReferenceSpec(
        "breaths/min", 12, 20, "adult_at_rest",
        "Kent NHS: Dysfunctional Breathing Pattern",
        "https://www.kentcht.nhs.uk/leaflet/dysfunctional-breathing-pattern/",
        "general adults at rest", "breaths counted in a quiet resting state", "2026-04-26",
        "Patient information, not a validated astronaut threshold.",
    ),
    "sleep_duration": ReferenceSpec(
        "h", 7, None, "adult_18_to_60; hours_per_day",
        "CDC: About Sleep",
        "https://www.cdc.gov/sleep/about/index.html/",
        "adults aged 18–60 years", "sleep duration per day; ASTRA method unrecorded", "2024-05-15",
        "Age and mission schedule are unrecorded; one episode is not a diagnosis.",
    ),
}

UNASSESSED_REASONS = {
    "sleep_quality": "internal_self_report_0_to_10_scale_no_clinical_cutoff",
    "exertion_fatigue": "internal_self_report_0_to_10_scale_no_clinical_cutoff",
    "activity": "steps_are_not_activity_minutes",
}


def compare_reference(observation: Observation) -> dict[str, Any]:
    """Compare one latest measurement only when its unit and scope are known."""

    review: dict[str, Any] = {
        "kind": "reference_review",
        "metric": observation.metric,
        "observation_id": observation.id,
        "synthetic": observation.synthetic,
        "status": "not_assessed",
        "reason": UNASSESSED_REASONS.get(observation.metric, "no_reference_rule"),
    }
    spec = REFERENCES.get(observation.metric)
    if spec is None:
        if observation.metric == "body_temperature" and observation.value_kind == "scalar" and observation.unit == "°C" and observation.scalar_value is not None:
            review.update({
                "status": "at_or_above_fever_threshold" if observation.scalar_value >= 38 else "below_fever_threshold",
                "reason": None, "value": observation.scalar_value,
                "reference_high": 38, "reference_unit": "°C",
                "description_ru": "38 °C — a common benchmark for high temperature in adults; a lower reading does not exclude illness",
                "source_title": "NHS: High temperature (fever) in adults",
                "source_url": "https://www.nhs.uk/symptoms/fever-in-adults/",
                "context": "terrestrial_adults; body_site_and_method_unrecorded",
                "population": "adults", "measurement_method": "thermometer; ASTRA method unrecorded",
                "limitations": "Individual temperature varies during the day; not a mission limit.",
            })
            return review
        if observation.metric == "blood_pressure" and observation.value_kind == "blood_pressure" and observation.unit == "mmHg" and observation.systolic is not None and observation.diastolic is not None:
            systolic, diastolic = observation.systolic, observation.diastolic
            if systolic >= 140 or diastolic >= 90:
                category, description = "bp_stage2_range", "range of stage 2 hypertension"
            elif systolic >= 130 or diastolic >= 80:
                category, description = "bp_stage1_range", "Stage 1 hypertension range"
            elif systolic >= 120 and diastolic < 80:
                category, description = "bp_elevated_range", "High blood pressure"
            else:
                category, description = "bp_normal_range", "Category of normal blood pressure"
            review.update({
                "status": category, "reason": None, "value": {"systolic": systolic, "diastolic": diastolic},
                "description_ru": description, "reference_unit": "mmHg",
                "source_title": "AHA/ACC 2025 High Blood Pressure Guideline",
                "source_url": "https://professional.heart.org/en/science-news/2025-high-blood-pressure-guideline/top-things-to-know",
                "context": "terrestrial_adults; single_reading_category_not_diagnosis",
            })
        return review
    review.update(
        {
            "reference_low": spec.lower,
            "reference_high": spec.upper,
            "reference_unit": spec.unit,
            "context": spec.context,
            "source_title": spec.source_title,
            "source_url": spec.source_url,
            "population": spec.population,
            "measurement_method": spec.measurement_method,
            "source_date": spec.source_date,
            "limitations": spec.limitations,
        }
    )
    if observation.value_kind != "scalar" or observation.scalar_value is None:
        review["reason"] = "unsupported_value_shape"
        return review
    if observation.unit != spec.unit:
        review["reason"] = "unit_not_comparable"
        return review
    value = observation.scalar_value
    review["value"] = value
    review["reason"] = None
    if value < spec.lower:
        review["status"] = "below_reference"
    elif spec.upper is not None and value > spec.upper:
        review["status"] = "above_reference"
    else:
        review["status"] = "meets_minimum" if spec.upper is None else "within_reference"
    return review
