"""Synthetic profiles exercise distinct paths without suggesting clinical validity."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select

from app.analytics import analyze_observations
from app.db import Database, sqlite_url, upgrade_database
from app.demo_seed import (STABLE_NAME, RESPIRATORY_NAME, SLEEP_NAME, PRESSURE_NAME,
                           RECOVERY_NAME, enrich_demo_profiles, extend_demo_histories, seed_demo_profiles)
from app.diagnostic_candidates import catalog, evaluate_candidates
from app.assistant import deterministic_explanation, permitted_summaries
from app.mission_context import mission_context_for
from app.complaint_parser import explicit_measurements, symptom_codes
from app.models import CrewMember, EnvironmentalMeasurement, Observation, SymptomReport


def test_reproducible_profiles_are_synthetic_distinct_and_non_destructive(tmp_path: Path) -> None:
    url = sqlite_url(tmp_path / "seed.sqlite3")
    upgrade_database(url)
    database = Database(url)
    try:
        with database.session_factory() as session:
            seeded = seed_demo_profiles(session)
            assert len(seeded) == 5
            assert [item["observations"] for item in seeded] == [216, 216, 216, 270, 216]
            assert session.scalar(select(func.count()).select_from(Observation)) == 1134
            assert session.scalar(select(func.count()).select_from(SymptomReport)) == 4
            assert session.scalar(select(func.count()).select_from(EnvironmentalMeasurement)) == 10
            enrich_demo_profiles(session)
            assert all(count == 0 for count in extend_demo_histories(session).values())
            assert session.scalar(select(func.count()).select_from(EnvironmentalMeasurement)) == 10
            assert session.scalar(select(func.count()).select_from(SymptomReport)) == 4
            assert session.scalar(select(func.count()).select_from(CrewMember)) == 5
            assert all(row.synthetic for row in session.scalars(select(Observation)))
            assert all(row.fictional for row in session.scalars(select(CrewMember)))
            assert {row.mission_location for row in session.scalars(select(CrewMember))} == {"iss", "moon", "mars"}

            plans = {}
            reports = {}
            explanations = {}
            for item in seeded:
                observations = list(session.scalars(select(Observation).where(Observation.crew_member_id == item["crew_id"])))
                symptom_rows = list(session.scalars(select(SymptomReport).where(SymptomReport.crew_member_id == item["crew_id"])))
                environment_rows = list(session.scalars(select(EnvironmentalMeasurement).where(EnvironmentalMeasurement.crew_member_id == item["crew_id"])))
                plan = analyze_observations(
                    observations, source_types={observations[0].source_id: "synthetic"},
                    symptom_reports=[{"id": row.id, "description": row.description} for row in symptom_rows],
                    environment_records=[{"id": row.id, "metric": row.metric, "value": row.value, "unit": row.unit, "synthetic": row.synthetic} for row in environment_rows],
                    mission_context=mission_context_for(session.get(CrewMember, item["crew_id"])),
                )
                plans[str(item["name"])] = {
                    row["metric"]: row for row in plan.facts if row.get("kind") == "parameter_assessment"
                }
                reports[str(item["name"])] = next(row for row in plan.facts if row.get("kind") == "integrated_report")
                response = {"facts": plan.facts, "integrated_report": reports[str(item["name"])]}
                explanations[str(item["name"])] = deterministic_explanation(response)
                assert permitted_summaries(response) == [explanations[str(item["name"])] ]
                assert len(explanations[str(item["name"])]) < 3000
            assert plans[STABLE_NAME]["heart_rate"]["status"] == "within_available_reference"
            assert plans[RESPIRATORY_NAME]["spo2"]["status"] == "diagnostic_candidate"
            assert plans[RESPIRATORY_NAME]["respiratory_rate"]["status"] == "outside_available_reference"
            assert plans[SLEEP_NAME]["sleep_duration"]["status"] == "diagnostic_candidate"
            assert plans[SLEEP_NAME]["exertion_fatigue"]["reference"]["status"] == "not_assessed"
            assert plans[STABLE_NAME]["activity"]["status"] == "descriptive_trend"
            recovery = plans[RECOVERY_NAME]["spo2"]
            assert "seven values" in recovery["series_insight"]["summary"]
            assert recovery["status"] == "within_available_reference"
            assert plans[PRESSURE_NAME]["blood_pressure"]["status"] == "diagnostic_candidate"
            assert reports[STABLE_NAME]["diagnostic_candidates"] == []
            assert "no diagnostic versions" in reports[STABLE_NAME]["overall_assessment"]
            assert [item["name"] for item in reports[RESPIRATORY_NAME]["diagnostic_candidates"]] == ["Possible hypoxemia"]
            assert [item["name"] for item in reports[SLEEP_NAME]["diagnostic_candidates"]] == ["Possible sleep deficit"]
            assert [item["name"] for item in reports[PRESSURE_NAME]["diagnostic_candidates"]] == ["Possible arterial hypertension (stage 2 range)", "Possible sleep apnea"]
            assert reports[STABLE_NAME]["mission_environment_context"]["location"] == "iss"
            assert reports[RESPIRATORY_NAME]["mission_environment_context"]["location"] == "moon"
            assert reports[SLEEP_NAME]["mission_environment_context"]["location"] == "mars"
            assert all(len(report["mission_environment_context"]["records"]) == 2 for report in reports.values())
            assert len(reports[PRESSURE_NAME]["condition_scenarios"]) == 2
            assert "Possible hypoxemia" in explanations[RESPIRATORY_NAME]
            assert "91 %" in explanations[RESPIRATORY_NAME]
            assert "Possible arterial hypertension" in explanations[PRESSURE_NAME]
            with pytest.raises(ValueError, match="not empty"):
                seed_demo_profiles(session)
    finally:
        database.dispose()


def test_diagnostic_catalog_needs_repeated_valid_evidence() -> None:
    assert {item["name_ru"] for item in catalog()["conditions"]} == {
        "Possible hypoxemia", "Possible arterial hypertension (stage 2 range)", "Possible sleep deficit", "Possible sleep apnea",
        "Possible head trauma, including concussion",
    }
    moment = datetime(2026, 11, 7, 8)
    def oxygen(value: float, day: int, flags: str = "[]") -> Observation:
        return Observation(id=f"oxygen-{day}", crew_member_id="demo", source_id="demo", metric="spo2",
                           value_kind="scalar", scalar_value=value, unit="%", observed_at=moment - timedelta(days=day),
                           observed_offset_minutes=0, synthetic=True, quality_flags_json=flags)
    assert evaluate_candidates([oxygen(91, 0)]) == []
    assert evaluate_candidates([oxygen(91, 0), oxygen(93, 1), oxygen(96, 2)])[0]["name"] == "Possible hypoxemia"
    assert evaluate_candidates([oxygen(91, 0, '["unreliable"]'), oxygen(93, 1), oxygen(94, 2)]) == []
    assert evaluate_candidates([oxygen(98, 0), oxygen(93, 1), oxygen(91, 2)]) == []


def test_independent_sourced_hypertension_and_sleep_apnea_case() -> None:
    """Unseen case: AHA pressure pattern plus NHLBI sleep-apnea symptom cluster."""
    base = datetime(2026, 11, 7, 8)
    pressures = [
        Observation(id=f"bp-{index}", crew_member_id="holdout", source_id="holdout",
                    metric="blood_pressure", value_kind="blood_pressure", systolic=systolic,
                    diastolic=diastolic, unit="mmHg", observed_at=base - timedelta(days=day, minutes=index),
                    observed_offset_minutes=0, synthetic=True, quality_flags_json="[]")
        for index, (day, systolic, diastolic) in enumerate(((1, 146, 94), (1, 148, 95), (0, 151, 96), (0, 149, 94)))
    ]
    complaint = "Напарник заметил громкий храп и остановки дыхания во сне, днём сильная сонливость."
    actual = {item["id"] for item in evaluate_candidates(pressures, [{"id": "case-1", "description": complaint}])}
    assert actual == {"D.POSSIBLE_HYPERTENSION", "D.POSSIBLE_SLEEP_APNEA"}
    assert {item["id"] for item in evaluate_candidates(pressures[:2], [{"id": "case-1", "description": complaint}])} == {"D.POSSIBLE_SLEEP_APNEA"}
    denied = "Храпа нет, остановок дыхания не отмечали, сонливости нет."
    assert symptom_codes(denied) == []
    assert {item["id"] for item in evaluate_candidates(pressures, [{"id": "case-2", "description": denied}])} == {"D.POSSIBLE_HYPERTENSION"}
    assert explicit_measurements("Болит голова, давление 150/95, пульс 90") == [
        {"metric": "blood_pressure", "value_kind": "blood_pressure", "systolic": 150, "diastolic": 95, "unit": "mmHg"},
        {"metric": "heart_rate", "value_kind": "scalar", "scalar_value": 90.0, "unit": "bpm"},
    ]


def test_head_injury_complaint_changes_analysis_actions_and_scenario() -> None:
    complaint = "Болит голова. Ударился ею. Течет кровь, тошнит"
    codes = set(symptom_codes(complaint))
    assert codes == {"headache", "head_impact", "external_bleeding", "nausea"}
    reports = [{"id": "head-event", "description": complaint}]
    plan = analyze_observations([], symptom_reports=reports)
    report = next(item for item in plan.facts if item.get("kind") == "integrated_report")
    candidate = next(item for item in report["diagnostic_candidates"] if item["id"] == "D.POSSIBLE_HEAD_INJURY")
    assert candidate["priority"] == "urgent_review"
    assert candidate["evidence_observation_ids"] == ["head-event"]
    assert "location and source of bleeding" in candidate["evidence"].lower()
    assert "concussion" in report["overall_assessment"]
    assert "urgently" in report["overall_assessment"]
    assert any(item["rule_id"] == "urgent_head_injury_pattern" for item in plan.findings)
    assert any(item["rule_id"] == "urgent_head_injury_pattern" for item in plan.alerts)
    assert any(step["candidate_id"] == candidate["id"] for step in report["next_steps"])
    assert any(scenario["candidate_id"] == candidate["id"] for scenario in report["condition_scenarios"])
    explanation = deterministic_explanation({"facts": plan.facts, "integrated_report": report})
    assert "Possible head trauma" in explanation
    assert "call a crew member" in explanation
    assert "clean cloth" in explanation
    assert len(explanation) < 3000


@pytest.mark.parametrize("complaint", [
    "Не ударялся головой. Болит голова, тошнит",
    "Ударился ногой, болит голова, тошнит",
    "Болит голова. Не ударился ею. Тошнит",
    "Ударился головой, но тошноты нет и головная боль отсутствует",
])
def test_head_injury_rule_does_not_infer_impact_or_negated_symptoms(complaint: str) -> None:
    assert not any(item["id"] == "D.POSSIBLE_HEAD_INJURY" for item in evaluate_candidates([], [{"id": "event", "description": complaint}]))


def test_head_injury_rule_does_not_join_unrelated_reports() -> None:
    reports = [
        {"id": "impact", "description": "Ударился головой, симптомов нет"},
        {"id": "nausea", "description": "Позже тошнит, голова не травмирована"},
    ]
    assert not any(item["id"] == "D.POSSIBLE_HEAD_INJURY" for item in evaluate_candidates([], reports))
