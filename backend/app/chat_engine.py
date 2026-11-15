"""Deterministic, offline dialogue grounded in the local catalog and records."""

from datetime import datetime
import re
from statistics import median
from typing import Any

from app.complaint_parser import symptom_codes
from app.complaint_review import NHS_URL, review_complaints
from app.diagnostic_candidates import evaluate_candidates
from app.models import Observation

FDA_URL = "https://www.fda.gov/consumers/consumer-updates/pulse-oximeter-basics"


def _oxygen_history(observations: list[Observation]) -> str | None:
    series = sorted((item for item in observations if item.metric == "spo2" and item.value_kind == "scalar"
                     and item.scalar_value is not None and item.unit == "%" and not item.withdrawn_at
                     and not item.superseded_by_id and not set(item.quality_flags) & {"invalid", "artifact", "unreliable", "stale"}),
                    key=lambda item: (item.observed_at, item.id))
    if not series:
        return None
    values = [float(item.scalar_value) for item in series[-8:]]
    recent = values[-7:]
    written = ", ".join(f"{value:g}" for value in values)
    if len(values) >= 8 and values[0] < 95 and all(value >= 95 for value in recent):
        return (f"Last {len(values)} SpO₂: {written} %. The low first value was an isolated occurrence in this window; "
                f"next {len(recent)} measurements — {min(recent):g}–{max(recent):g} %, last {values[-1]:g} %. "
                "No sustained decline in the last points. Clarify the device, signal quality, and symptoms during the low reading.")
    if len(recent) >= 4:
        first = median(recent[:3])
        last = median(recent[-3:])
        direction = "decreased" if last < first - 1 else "increased" if last > first + 1 else "remained substantially unchanged"
        return (f"Last SpO₂: {written} %. Median of the last three points {last:g} % versus {first:g} % "
                f"at the beginning of the seven-point window: series {direction}. Last value {values[-1]:g} %. "
                "If low values repeat or there is shortness of breath, report to the medical officer.")
    return f"SpO₂ recorded: {written} %. More comparable points are needed for the series direction."


def reply_to_message(messages: list[str], observations: list[Observation], analysis: dict[str, Any]) -> tuple[str, list[str]]:
    """Use only recent user turns from this profile; return answer and public source URLs."""
    current = messages[-1].casefold()
    combined = ". ".join(messages[-5:])
    codes = set(symptom_codes(combined))
    virtual_report = {"id": "current_chat_context", "description": combined, "observed_at": datetime.utcnow().isoformat() + "Z"}
    candidates = evaluate_candidates(observations, [virtual_report])
    urgent = next((item for item in candidates if item["id"] == "D.POSSIBLE_HEAD_INJURY"), None)
    if urgent:
        urls = [source["url"] for source in urgent["sources"]]
        return (
            f"Preliminary assessment: {urgent['name']}. {urgent['evidence']} "
            "Stop working, ask someone nearby to stay with you, and tell the flight medical officer. "
            "For bleeding from a head wound, apply a clean cloth to the bleeding site; if there may be a depressed skull injury or an object in the wound, do not press on it. "
            "Do not stay alone. Report when the impact occurred and whether there was loss of consciousness, repeated vomiting, confusion, worsening pain, or a change in vision. "
            "This determines the urgency of further assistance; an exact diagnosis cannot be established by correspondence.", urls)
    if "head_impact" in codes:
        return ("You reported a blow to the head. Is there now increasing headache, nausea or vomiting, blood, "
                "loss of consciousness, confusion, or a change in vision? When did the impact occur? "
                "If symptoms are worsening, stop work and immediately call someone nearby and the flight medic.",
                ["https://www.nhs.uk/conditions/head-injury-and-concussion/"])
    if "external_bleeding" in codes or any(word in combined.casefold() for word in ("порез", "рана", "рану", "cut", "wound")):
        _, actions, _ = review_complaints([virtual_report])
        if actions:
            text = combined.casefold()
            no_object = bool(re.search(r"(?:предмет\w*\s+в\s+ран\w*\s+нет|нет\s+(?:в\s+ран\w*\s+)?предмет\w*|предмет\w*\s+нет|no (?:object|foreign body) in the wound)", text))
            embedded = not no_object and bool(re.search(r"(?:торчит|застрял|застрявш\w*)\s+(?:\w+\s+){0,2}(?:предмет|осколок)|предмет\s+в\s+ран\w*|(?:lodged|embedded) object", text))
            first_aid = ("You reported no object in the wound. Apply continuous direct pressure with a clean cloth. "
                         if no_object else "If an object is embedded, do not remove it; press around the wound edges. "
                         if embedded else "If there is no embedded object, press the wound with a clean cloth. If there is one, do not remove it; press around it. ")
            question = ("Is blood still flowing, and how much? Is the wound deep, or is there weakness, numbness, or loss of movement? "
                        if no_object or embedded else "Is blood still flowing, and how much? Is an object embedded, is the wound deep, or is there weakness, numbness, or loss of movement? ")
            return ("A wound with bleeding has been reported. Stop working and call someone nearby. " + first_aid + question +
                    "If the bleeding does not stop or if these signs are present, urgently call the flight medic.", [NHS_URL])
        return ("Describe the location and depth of the wound, whether blood is still flowing, and whether an object is lodged. "
                "In case of severe bleeding, call someone nearby and the flight medic immediately.", [NHS_URL])
    if "headache" in codes:
        return ("You reported a headache. When did it start, and how severe is it on a scale of 0–10? "
                "Was there a head injury, nausea, vomiting, vision changes, or weakness? "
                "If you measured blood pressure or temperature, provide the values with units. "
                "In case of sudden severe pain or neurological symptoms, call for help immediately.",
                ["https://www.nhs.uk/symptoms/headaches/"])
    if any(token in current for token in ("spo2", "spо2", "spo₂", "spо₂", "сатурац", "кислород")):
        history = _oxygen_history(observations)
        return ((history or "There are no SpO₂ records in this profile yet. Please provide the values and dates of measurements.") +
                " A published reference for most healthy people is 95–100%, but readings depend on measurement conditions and symptoms.", [FDA_URL])
    if candidates:
        candidate = candidates[0]
        return (f"Preliminary assessment based on saved data: {candidate['name']}. {candidate['evidence']} "
                f"For clarification: {' '.join(candidate['missing_confirmation'][:2])} "
                "If the condition is worsening now, inform the flight medical officer.",
                [source["url"] for source in candidate["sources"]])
    report = analysis.get("integrated_report") or {}
    saved = report.get("diagnostic_candidates") or []
    if any(token in current for token in ("состояни", "анализ", "результат", "показател", "condition", "analysis", "result", "indicator")) and saved:
        candidate = saved[0]
        return (f"Preliminary assessment based on the profile history: {candidate['name']}. {candidate['evidence']} "
                f"What to clarify: {' '.join(candidate['missing_confirmation'][:2])}",
                [source["url"] for source in candidate["sources"]])
    return ("I saved the message. Please clarify what is bothering you, when it started, and what has changed; "
            "if there are measurements, write the indicator and number. A single unclear message cannot determine a specific cause.", [])
