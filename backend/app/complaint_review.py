"""Review explicit symptom reports without turning prose into an examination."""

import re
from typing import Any

from app.complaint_parser import normalize_english, symptom_codes

NHS_URL = "https://www.nhs.uk/conditions/cuts-and-grazes/"
RED_CROSS_URL = "https://www.redcross.org/take-a-class/resources/learn-first-aid/bleeding-life-threatening-external"
NASA_URL = "https://www.nasa.gov/reference/6-0-medical-operations/"

SYMPTOM_NAMES = {
    "external_bleeding": "reported external hemorrhage",
    "head_impact": "reported head trauma",
    "headache": "headache",
    "nausea": "nausea",
    "vomiting": "vomiting",
    "dyspnea": "difficulty breathing",
    "chest_pain": "chest pain",
    "vision_change": "visual changes",
    "loud_snoring": "snoring",
    "witnessed_breathing_pauses": "witnessed breathing pauses during sleep",
    "daytime_sleepiness": "daytime sleepiness",
}


def review_complaints(reports: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any] | None]:
    reviews: list[dict[str, Any]] = []
    wound_actions: list[dict[str, Any]] = []
    wound_scenario: dict[str, Any] | None = None
    for report in sorted(reports, key=lambda item: (str(item.get("observed_at", "")), str(item.get("id", ""))), reverse=True):
        description = str(report.get("description", ""))
        codes = symptom_codes(description)
        normalized = normalize_english(description).casefold()
        cut = bool(re.search(r"\b(?:порез\w*|ран\w*|царап\w*)\b", normalized))
        finger = bool(re.search(r"\b(?:палец|пальц\w*|finger)\b", normalized))
        arm = bool(re.search(r"\b(?:рук\w*|предплеч\w*|локт\w*|finger|hand|arm|wrist)\b", normalized))
        elbow = bool(re.search(r"\bлокт\w*\b|\belbow\b", normalized))
        dark = bool(re.search(r"\bт[её]мн\w*\s+кров\w*\b|\bdark blood\b", normalized))
        visible_wound = cut and "external_bleeding" in codes
        location = "finger" if finger else "elbow area on the arm" if elbow and arm else "arm" if arm else None
        known = ["The complaint text is preserved verbatim; this is a message from the person, not the result of an examination."]
        if visible_wound:
            known.append("A cut and external bleeding are reported" + (f" ({location})" if location else "") + ".")
        if dark:
            known.append("The author describes the blood as dark; the color does not establish the vessel, volume, or severity of the bleeding.")
        unknowns = []
        if visible_wound:
            unknowns = [
                "Is the bleeding continuing, what is the volume and rate?",
                "What is the depth of the wound and is there an object in it?",
                "Are movement and sensitivity of the hand preserved; is there weakness or dizziness?",
            ]
        review = {
            "report_id": str(report.get("id", "")),
            "description": description,
            "observed_at": report.get("observed_at"),
            "recorded_at": report.get("recorded_at"),
            "source_id": report.get("source_id"),
            "source_type": report.get("source_type"),
            "source_title": report.get("source_title"),
            "synthetic": bool(report.get("synthetic", False)),
            "location": location,
            "recognized_symptoms": [SYMPTOM_NAMES[code] for code in codes if code in SYMPTOM_NAMES],
            "known": known,
            "unknowns": unknowns,
            "interpretation": "A possible external wound is mentioned in the narrative; the diagnosis, type of vessel, and severity cannot be established from a single description." if visible_wound else "Only clearly described symptoms are recognized; the cause and diagnosis are not established.",
            "status": "reported_visible_wound" if visible_wound else "reported_symptoms",
        }
        reviews.append(review)
        if visible_wound and not wound_actions:
            base = {
                "report_id": review["report_id"],
                "source_scope": "General Earth first aid; on board, the mission-approved procedure takes priority.",
                "source_reviewed_at": "2026-11-08",
            }
            wound_actions = [
                {**base, "order": 1, "category": "first_aid", "kind": "wound_pause_notify", "statement": "Stop current work, call a crew member, and report the cut and bleeding to the onboard medical officer.", "why": "External bleeding has been reported; assistance and examination may be needed immediately.", "condition": "If the event is current; the exact intensity of the bleeding is still unknown.", "escalation": "Act according to the approved mission procedure; if communication is available, call for ground medical support.", "source_title": "NASA: Medical Operations", "source_url": NASA_URL, "sources": [{"title": "NASA: Medical Operations", "url": NASA_URL}, {"title": "NHS: Cuts and grazes", "url": NHS_URL}]},
                {**base, "order": 2, "category": "collect_more_data", "kind": "wound_check_object", "statement": "Clarify if there is an embedded object in the wound, if bleeding is continuing, how deep the wound is, and if movement and sensation in the hand are preserved.", "why": "These findings change the safe actions and urgency of the assessment; the color of the blood does not determine this.", "condition": "Do not delay assistance for the sake of gathering information, if bleeding is continuing or condition is worsening.", "escalation": "If there is a deep wound, movement, or sensation loss, consult the onboard medic.", "source_title": "NHS: Cuts and grazes", "source_url": NHS_URL},
                {**base, "order": 3, "category": "first_aid", "kind": "wound_pressure_no_object", "statement": "If there is no object in the wound, apply clean cloth or bandage directly and continuously to the bleeding site.", "why": "Direct pressure is the standard first step for external bleeding.", "condition": "Only if there is no lodged object in the wound; do not assume based on the color of the blood.", "escalation": "If the bleeding does not stop or the bleeding is severe, immediately call the flight medic and initiate the mission procedure.", "source_title": "NHS: Cuts and grazes", "source_url": NHS_URL, "source_date": "2026-04-02", "sources": [{"title": "NHS: Cuts and grazes", "url": NHS_URL}, {"title": "Red Cross: Life-Threatening External Bleeding", "url": RED_CROSS_URL}]},
                {**base, "order": 4, "category": "first_aid", "kind": "wound_object_branch", "statement": "If an object is lodged in the wound, do not remove it or apply pressure directly to it; instead, apply pressure around the object by compressing the edges of the wound.", "why": "Removing the object and applying pressure directly on it may worsen the injury.", "condition": "Only if a truly lodged object is indeed present; its presence is currently unknown.", "escalation": "Transfer the assessment and further actions to the flight medic according to the mission procedure.", "source_title": "NHS: Cuts and grazes", "source_url": NHS_URL},
                {**base, "order": 5, "category": "first_aid", "kind": "wound_clean_if_minor", "statement": "If the bleeding has stopped and the wound is minor, clean it and cover it with a clean dressing.", "why": "This is general care for a minor cut after the bleeding has stopped.", "condition": "Do not use this as a substitute for assessment in the case of a deep wound, ongoing bleeding, or worsening condition.", "escalation": "If there are signs of infection or suspicion of deep wound, consult the flight medic.", "source_title": "NHS: Cuts and grazes", "source_url": NHS_URL},
                {**base, "order": 6, "category": "escalation", "kind": "wound_urgent_signs", "statement": "If there is unceasing or heavy bleeding, deep wound, loss of sensitivity or movement of the hand, marked weakness or fainting, urgently call the flight medic.", "why": "These are signs where self-care may be insufficient.", "condition": "If any of the signs are present or cannot be safely ruled out.", "escalation": "Follow the established mission procedure and if communication is available, contact ground medical support.", "source_title": "NHS: Cuts and grazes", "source_url": NHS_URL, "source_date": "2026-04-02", "sources": [{"title": "NHS: Cuts and grazes", "url": NHS_URL}, {"title": "NASA: Medical Operations", "url": NASA_URL}]},
            ]
            wound_scenario = {
                "status": "qualitative_conditional_not_individual_prediction",
                "initial_event": "Reported cut " + (f"in the area {location}" if location else "uncertain localization") + " and external bleeding.",
                "involved_systems": ["skin and soft tissues", "Circulation with ongoing blood loss"],
                "possible_branches": ["Small wound with stopped bleeding after assistance", "Ongoing bleeding or signs of deeper tissue damage require urgent assessment"],
                "follow_recommendations": "With appropriate first aid, bleeding may stop and the wound may be protected; individual outcome is unknown.",
                "ignore_recommendations": "If bleeding continues without assistance, further blood loss is possible; volume and outcome are unknown.",
                "uncertainty": "Depth, volume of blood loss, condition of the hand, and presence of an object are unknown; timeframes and probability of outcomes are not calculated.",
                "source_title": "NHS: Cuts and grazes",
                "source_url": NHS_URL,
                "source_date": "2026-04-02",
                "sources": [{"title": "NHS: Cuts and grazes", "url": NHS_URL}, {"title": "Red Cross: Life-Threatening External Bleeding", "url": RED_CROSS_URL}],
                "source_scope": "General Earth first aid, not a verified ISS medical protocol.",
            }
    for step in wound_actions:
        if step.get("source_url") == NHS_URL:
            step.setdefault("source_date", "2026-04-02")
    return reviews, wound_actions, wound_scenario
