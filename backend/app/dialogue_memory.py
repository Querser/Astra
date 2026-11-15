"""Profile-scoped conversation state. Only advance() can write user facts.

The database owns the transcript. This projection holds the active episode and
the sources of its facts; starting an unrelated episode resets the projection.
"""
import re
from copy import deepcopy

from app.complaint_parser import explicit_measurements, normalize_english, symptom_codes


TARGETS = {
    "vomiting": r"\u0440\u0432\u043e\u0442|\u0440\u0432\u0430\u043b\u043e|\u0432\u044b\u0440\u0432\u0430\u043b|vomit|throw up",
    "nausea": r"\u0442\u043e\u0448\u043d|nausea",
    "dizziness": r"\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436|\u043a\u0440\u0443\u0436\u0438\u0442\u0441\u044f \u0433\u043e\u043b\u043e\u0432\u0430|dizz",
    "associated_symptoms": r"\u0441\u043e\u043f\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0449|\u0434\u0440\u0443\u0433\u0438\u0435 \u0441\u0438\u043c\u043f\u0442\u043e\u043c\u044b|\u0434\u0440\u0443\u0433\u0438\u0445 \u0441\u0438\u043c\u043f\u0442\u043e\u043c|other symptoms|associated symptoms",
    "pain_course": r"\u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442|\u0434\u0435\u0440\u0436\u0438\u0442\u0441\u044f|\u043e\u0441\u043b\u0430\u0431\u0435\u0432\u0430|\u0443\u0441\u0438\u043b\u0438\u0432\u0430|\u0443\u043c\u0435\u043d\u044c\u0448\u0430|\u043d\u0430\u0440\u0430\u0441\u0442\u0430|\u0441\u0442\u0438\u0445\u0430\u0435\u0442|\u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f|improv|worsen|still hurt|gone away",
    "pain_score": r"\u043f\u043e \u0441\u0438\u043b\u0435|\u0441\u0438\u043b\u044c\u043d|\u0438\u043d\u0442\u0435\u043d\u0441\u0438\u0432\u043d\u043e\u0441\u0442|\u0448\u043a\u0430\u043b\u0435|\u0431\u0430\u043b\u043b|\u0438\u0437 10|/10|\u0441\u0438\u043b[\u0430\u0443] \u0431\u043e\u043b\u0438|how severe|pain score|out of 10",
    "onset": r"\u043a\u0430\u043a \u0434\u0430\u0432\u043d\u043e|\u043a\u043e\u0433\u0434\u0430.{0,24}(?:\u043d\u0430\u0447|\u043f\u043e\u044f\u0432)|\u043d\u0430\u0447\u0430(?:\u043b|\u043b\u043e)|when.{0,30}(?:start|begin)|how long",
    "blood_pressure": r"\u0434\u0430\u0432\u043b\u0435\u043d\u0438|\u0442\u043e\u043d\u043e\u043c\u0435\u0442\u0440|\u0434\u0432\u0430 \u0447\u0438\u0441\u043b\u0430",
    "measurement_time": r"\u043a\u043e\u0433\u0434\u0430.{0,45}(?:\u0438\u0437\u043c\u0435\u0440|\u043c\u0435\u0440\u0438\u043b)|\u0432\u0440\u0435\u043c\u044f.{0,10}\u0438\u0437\u043c\u0435\u0440",
    "body_temperature": r"\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440",
    "head_impact": r"\u0443\u0434\u0430\u0440|\u0442\u0440\u0430\u0432\u043c",
    "diarrhea": r"\u043f\u043e\u043d\u043e\u0441|\u0434\u0438\u0430\u0440\u0435",
    "weakness": r"\u0441\u043b\u0430\u0431\u043e\u0441\u0442",
    "speech_change": r"\u043d\u0430\u0440\u0443\u0448\u0435\u043d\u0438\w* \u0440\u0435\u0447\u0438",
    "fluid_tolerance": r"(?:\u043c\u043e\u0436\u0435\u0442\u0435|\u0443\u0434\u0430[\u0435\u0451]\u0442\u0441\u044f|\u043f\u043e\u043b\u0443\u0447\u0430\u0435\u0442\u0441\u044f)\s+(?:\u043b\u0438\s+)?\u043f\u0438\u0442\u044c",
    "neck_swelling": r"\u0448\u0435[\u044f\u0438\u044e]\s+\u043e\u043f\u0443\u0445|\u043e\u043f\u0443\u0445\w*\s+\u0448\u0435[\u044f\u0438\u044e]|\u043e\u0442[\u0435\u0451]\u043a\w*\s+\u0448\u0435[\u044f\u0438\u044e]",
    "dehydration": r"\u043e\u0431\u0435\u0437\u0432\u043e\u0436|\u0441\u0443\u0445\u043e\u0441\u0442\w*\s+\u0432\u043e\s+\u0440\u0442\u0443|\u043c\u043e\u0447\u0435\u0438\u0441\u043f\u0443\u0441\u043a\u0430\u043d",
    "fluid_intake": r"\b(?:\u043f\u0438\u043b|\u043f\u0438\u043b\u0430|\u043f\u0438\u043b\u0438|\u0432\u044b\u043f\u0438\u043b\w*|\u0432\u044b\u043f\u0438\u043b\u0430\w*)\b|\u043f\u0438\u043b\w*\s+\u0432\u043e\u0434\u0443",
}
YES = {"\u0434\u0430", "\u0435\u0441\u0442\u044c", "\u0430\u0433\u0430"}
NO = {"\u043d\u0435\u0442", "\u043d\u0435\u0442\u0443", "\u043d\u0435 \u0431\u044b\u043b\u043e", "\u043d\u0435 \u043d\u0430\u0431\u043b\u044e\u0434\u0430\u043b", "\u043d\u0435 \u043d\u0430\u0431\u043b\u044e\u0434\u0430\u043b\u0430"}
UNCERTAIN = re.compile(r"\u043d\u0435 \u0437\u043d\u0430\u044e|\u043d\u0435 \u0443\u0432\u0435\u0440\u0435\u043d|\u043d\u0435 \u043f\u043e\u043c\u043d\u044e|\u0437\u0430\u0442\u0440\u0443\u0434\u043d\u044f\u044e\u0441\u044c")
NON_REPORT = re.compile(r"\b(?:\u0435\u0441\u043b\u0438|\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c|\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440|\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e|\u043d\u0430\u0432\u0435\u0440\u043d\u043e\u0435|\u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c|\u0432\u0440\u044f\u0434 \u043b\u0438|\u043a\u0430\u0436\u0435\u0442\u0441\u044f)\b")
SCORE = re.compile(r"(?<!\d)(10|[0-9])\s*(?:\u0438\u0437\s*10|/\s*10|\u0431\u0430\u043b\u043b\w*)\b")
TIME = re.compile(r"\b(?:\u0441 \u0443\u0442\u0440\u0430|\u0443\u0442\u0440\u043e\u043c|\u0432\u0435\u0447\u0435\u0440\u043e\u043c|\u043d\u043e\u0447\u044c\u044e|\u043f\u043e\u043b\u0447\u0430\u0441\u0430 \u043d\u0430\u0437\u0430\u0434|(?:\d+|\u0447\u0430\u0441|\u0434\u0432\u0430|\u0442\u0440\u0438|\u043f\u044f\u0442\u044c)\s*(?:\u043c\u0438\u043d\u0443\u0442\w*|\u0447\u0430\u0441\w*)?\s+\u043d\u0430\u0437\u0430\u0434|\d{1,2}:\d{2})\b")
PAIN_TOPICS = {"headache", "fever_headache", "head", "food", "chest_pain"}
OTHER_PAIN = re.compile(r"\b(?:\u0431\u043e\u043b\u0438\u0442|\u0437\u0430\u0431\u043e\u043b\u0435\u043b[\u0430\u0438]?)\s+(?P<site>\u0441\u043f\u0438\u043d\u0430|\u043f\u043e\u044f\u0441\u043d\u0438\u0446\u0430|\u043a\u043e\u043b\u0435\u043d\u043e|\u043f\u043b\u0435\u0447\u043e|\u043d\u043e\u0433\u0430|\u0440\u0443\u043a\u0430|\u0448\u0435\u044f|\u0443\u0445\u043e|\u0437\u0443\u0431)\b")


def resolved_complaint(text, topic):
    phrase = normalize_english(text).replace("\u0451", "\u0435")
    if re.search(r"\b\u0432\u0441\u0435\s+\u043f\u0440\u043e\u0448\u043b\u043e\b|\b\u043d\u0435\u0442\s+\u0431\u043e\u043b\u0438\s+\u0438\s+\u0434\u0440\u0443\u0433\u0438\u0445\s+(?:\u043f\u0440\u0438\u0437\u043d\u0430\u043a\u043e\u0432|\u0441\u0438\u043c\u043f\u0442\u043e\u043c\u043e\u0432)\b", phrase):
        return True
    if re.search(r"\b(?:\u0431\u043e\u043b\u044c|\u0433\u043e\u043b\u043e\u0432\u0430|\u0441\u0438\u043c\u043f\u0442\u043e\u043c\w*)\s+(?:\u043f\u043e\u043b\u043d\u043e\u0441\u0442\u044c\u044e\s+)?\u043f\u0440\u043e\u0448\u043b\w*|\b\u0431\u043e\u043b\u044c\u0448\u0435\s+\u043d\u0435\s+\u0431\u043e\u043b\u0438\u0442\b|\b\u0431\u043e\u043b\u0438\s+\u043d\u0435\u0442\b", phrase):
        return True
    return topic == "food" and bool(re.search(r"\b\u0436\u0438\u0432\u043e\u0442\s+(?:\u043f\u043e\u043b\u043d\u043e\u0441\u0442\u044c\u044e\s+)?\u043f\u0440\u043e\u0448[\u0435\u0451]\u043b\b|\b\u0436\u0438\u0432\u043e\u0442\s+\u0431\u043e\u043b\u044c\u0448\u0435\s+\u043d\u0435\s+\u0431\u043e\u043b\u0438\u0442\b", phrase))


def _question(text, assistant_id, topic):
    parts = re.findall(r"[^.?!\n]*\?", text)
    if not parts:
        parts = re.findall(r"(?:\u0443\u0442\u043e\u0447\u043d\u0438\u0442\u0435|\u0441\u043a\u0430\u0436\u0438\u0442\u0435|\u0441\u043e\u043e\u0431\u0449\u0438\u0442\u0435|\u043d\u0430\u043f\u0438\u0448\u0438\u0442\u0435|\u043f\u0440\u043e\u0432\u0435\u0440\u044c(?:\u0442\u0435)?\s*,?\s*\u043d\u0435\s+\u0431\u044b\u043b\u043e\s+\u043b\u0438)[^.?!\n]*", text, re.I)[-1:]
    if not parts:
        return None
    wording = " ".join(part.strip() for part in parts)[-400:]
    lower = normalize_english(wording)
    targets = [key for key, pattern in TARGETS.items() if re.search(pattern, lower)]
    # "Do you have nausea or vomiting?" is a yes/no symptom screen. An answer
    # to "Is it improving or persisting?" must instead specify an alternative.
    polar = bool(re.search(r"\b(\u0435\u0441\u0442\u044c \u043b\u0438|\u0431\u044b\u043b[\u0430\u0438\u043e]? \u043b\u0438|\u043d\u0435 \u0431\u044b\u043b\u043e \u043b\u0438|\u043d\u0430\u0431\u043b\u044e\u0434\u0430\w* \u043b\u0438|\u0431\u044b\u0432\u0430\w* \u043b\u0438|\u043c\u043e\u0436\u0435\u0442\u0435 \u043b\u0438|\u0443\u0434\u0430[\u0435\u0451]\u0442\u0441\u044f \u043b\u0438|\u0442\u044b \u0443\u0436\u0435 \u043f\u0438\u043b|\u0432\u044b \u0443\u0436\u0435 \u043f\u0438\u043b\u0438|\u043f\u0438\u043b[\u0430\u0438]? \u043b\u0438|\u0432\u0430\u0441 \u0442\u043e\u0448\u043d\u0438\u0442|\u0442\u043e\u0448\u043d\u0438\u0442|\u0440\u0432\u043e\u0442\u0430 \u0435\u0441\u0442\u044c|have you|do you|did you|are you|is there|any)\b", lower))
    expected = "open"
    if (" \u0438\u043b\u0438 " in lower or " or " in lower) and not polar:
        expected = "choice"
    elif polar and not re.search(r"\b(?:\u0441\u043a\u043e\u043b\u044c\u043a\u043e|\u043a\u043e\u0433\u0434\u0430|\u043d\u0430\u0441\u043a\u043e\u043b\u044c\u043a\u043e|\u043a\u0430\u043a\u0438\u0435|how many|how long|when|which)\b", lower):
        expected = "boolean"
    elif "blood_pressure" in targets or "pain_score" in targets or "body_temperature" in targets:
        expected = "numeric"
    if len(parts) > 1:
        expected = "open"
    return {"text": wording, "assistant_message_id": str(assistant_id), "topic": topic,
            "expected": expected, "targets": targets, "status": "unresolved"}


def delivered(memory, assistant_message_id, text):
    result = deepcopy(memory or {})
    question = _question(text, assistant_message_id, result.get("topic", "general"))
    if question:
        result["open_question"] = question
    return result


def _topic(text, codes, previous):
    if previous in {"fever", "fever_headache"} and re.search(r"\b(?:\u043f\u0438\u0441\u0430\u043b|\u0433\u043e\u0432\u043e\u0440\u0438\u043b|\u0442\u043e\u043b\u044c\u043a\u043e \u0447\u0442\u043e|\u043d\u0435 \u0434\u0443\u043c\u0430\u044e|\u0432\u044b\u043f\u043e\u043b\u043d\u044f\u044e \u0434\u0435\u0439\u0441\u0442\u0432\u0438\u044f)\b", text) and re.search(r"\u043f\u043e\u0440\u0435\u0437|\u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447", text):
        return previous
    if "head_impact" in codes:
        return "head"
    if previous in {"headache", "head"} and re.search(r"\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*)\b", text):
        return "head"
    if "external_bleeding" in codes or re.search(r"\b\u043f\u043e\u0440\u0435\u0437\u0430\u043b\w*", text):
        return "bleeding"
    if "headache" in codes or re.search(r"\u0433\u043e\u043b\u043e\u0432\u0430 \u0431\u043e\u043b\u0438\u0442|\u0440\u0430\u0437\u0431\u043e\u043b\u0435\u043b\u0430\u0441\u044c \u0433\u043e\u043b\u043e\u0432\u0430", text):
        return "fever_headache" if "fever" in codes else "headache"
    if "abdominal_pain" in codes or re.search(r"\u0436\u0438\u0432\u043e\u0442.{0,12}(?:\u043a\u0440\u0443\u0442\u0438\u0442|\u0431\u043e\u043b\u0438\u0442)", text):
        return "food"
    if "chest_pain" in codes:
        return "chest_pain"
    site = OTHER_PAIN.search(text)
    if site:
        return "pain_" + site["site"]
    if "fever" in codes and previous == "headache":
        return "fever_headache"
    if "fever" in codes:
        return "fever"
    if re.search(r"\u0441\u0430\u0442\u0443\u0440\u0430\u0446|spo[2₂]", text):
        return "oxygen"
    if re.search(r"\u0434\u0430\u0432\u043b\u0435\u043d\u0438|\u0442\u043e\u043d\u043e\u043c\u0435\u0442\u0440", text) and (previous == "general" or "\u0434\u0440\u0443\u0433\u0430\u044f" in text):
        return "blood_pressure"
    return previous


def _denied(text, pattern):
    """Scope an explicit negative to a symptom or a coordinated symptom list."""
    for clause in re.split(r"[.,;!?]|\s+(?:\u043d\u043e|\u0430)\s+|\s+\u0438\s+(?=(?:\u0435\u0441\u0442\u044c|\u043d\u0435\u0442|\u0431\u0435\u0437)\b)", text):
        for match in re.finditer(pattern, clause):
            before, after = clause[:match.start()], clause[match.end():]
            if re.search(r"\b\u043d\u0435\s+$", before) and re.match(r"(?:\u0440\u0432\u0430\u043b\u043e|\u0432\u044b\u0440\u0432\u0430\u043b|\u0442\u043e\u0448\u043d|\u043a\u0440\u0443\u0436\u0438\u0442\u0441\u044f)", match[0]):
                return True
            if re.search(r"\b(?:\u0431\u0435\u0437|\u043d\u0435\u0442|\u043d\u0435 \u0431\u044b\u043b\u043e|\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\u044e\u0442)\s+(?:\w+\s+\u0438\s+)?$", before):
                return True
            if re.match(r"\w*\s+(?:\u0438\s+\w+\s+)?(?:\u043d\u0435\u0442|\u043d\u0435 \u0431\u044b\u043b\u043e|\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\w*)\b", after):
                return True
    return False


def advance(memory, user_message_id, text):
    current = deepcopy(memory or {})
    if current.get("episode_resolved") and symptom_codes(text):
        current = {"medical_history": current.get("medical_history", [])}
    previous = current.get("topic", "general")
    q = current.get("open_question") or {}
    pending = q.get("status") == "unresolved"
    raw = normalize_english(text).replace("\u0451", "\u0435").replace("\u0442\u0435\u043c\u043f\u0438\u0440\u0430\u0442\u0443\u0440", "\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440").strip()
    phrase = raw.strip(" \t\n.,!?")
    # Only assert facts from declarative clauses. A follow-up question may
    # include sample readings, symptoms, or another person's measurements.
    reported = []
    for sentence in re.finditer(r"(.+?)([!?]|\.(?!\d)|$)", raw, re.S):
        content, terminator = sentence.groups()
        if terminator == "?" or NON_REPORT.search(content) or UNCERTAIN.search(content):
            continue
        reported.append(content)
    statement = ". ".join(reported).strip(" \t\n.,!?")
    codes = set(symptom_codes(statement))
    topic = _topic(statement, codes, previous)
    changed = topic != previous
    if changed and not ({previous, topic} <= {"head", "headache", "fever_headache"}):
        # Keep episodes independent; nearby dialogue is supplied separately
        # to preserve cross-topic context without treating old facts as current.
        current = {"medical_history": current.get("medical_history", [])}
        q, pending = {}, False
    current["topic"] = topic
    facts = current.setdefault("facts", [])
    targets = q.get("targets", []) if pending else []
    update = {"kind": "new_topic" if changed else "other", "keys": []}
    current["last_update"] = update
    source = str(user_message_id)

    def add(key, value, kind, linked=False):
        prior = next((f for f in reversed(facts) if f["key"] == key and f["status"] == "active"), None)
        if prior:
            prior.update(status="superseded", superseded_by=source)
            if prior["value"] != value and re.search(r"\u043f\u043e\u043f\u0440\u0430\u0432|\u0443\u0442\u043e\u0447\u043d|\u043e\u0448\u0438\u0431|\u0442\u043e\u0447\u043d\u0435\u0435|\u043f\u0435\u0440\u0435\u043f\u0443\u0442|\u043d\u0435 .+[, ]\u0430 ", phrase):
                update["kind"] = "correction"
        fact = {"key": key, "value": value, "kind": kind, "user_message_id": source, "status": "active"}
        if pending and (linked or key in targets):
            fact["question_id"] = q["assistant_message_id"]
        facts.append(fact)
        update["keys"].append(key)

    resolved = resolved_complaint(text, topic)
    neck_still_swollen = any(f.get("key") == "neck_swelling" and f.get("value") is True and f.get("status") == "active" for f in facts)
    complete = bool(re.search(r"\u0432\u0441[\u0435\u0451]\s+\u043f\u0440\u043e\u0448\u043b\u043e|\u043e\u0442[\u0435\u0451]\u043a\s+\u0448\u0435\u0438\s+\u043f\u0440\u043e\u0448[\u0435\u0451]\u043b|\u0448\u0435\u044f\s+\u0431\u043e\u043b\u044c\u0448\u0435\s+\u043d\u0435\s+\u043e\u043f\u0443\u0445", text, re.I))
    if resolved:
        was_resolved = bool(current.get("episode_resolved"))
        update["kind"] = ("partial_resolution" if neck_still_swollen and not complete else
                          "resolution_confirmed" if was_resolved else "resolution")
        current["episode_resolved"] = update["kind"] != "partial_resolution"
        if topic == "food":
            add("abdominal_pain", False, "denial")
        elif topic in {"headache", "head", "fever_headache"}:
            add("headache", False, "denial")
        add("pain_course", "\u043f\u0440\u043e\u0448\u043b\u0430", "change")
        if pending:
            q.update(status="resolved", resolved_by=source)
        current["open_question"] = q
        return current

    if phrase in {"\u043f\u0440\u0438\u0432\u0435\u0442", "\u0437\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435", "\u0434\u043e\u0431\u0440\u044b\u0439 \u0434\u0435\u043d\u044c"}:
        update["kind"] = "greeting"
        return current
    if "?" in text and re.match(r"(\u043c\u043e\u0436\u0435\u0442 \u043b\u0438|\u0430 \u0435\u0441\u043b\u0438|\u0447\u0442\u043e \u0435\u0441\u043b\u0438|\u0430 \u0432\u0434\u0440\u0443\u0433|\u043c\u043e\u0436\u0435\u0442 \u0431\u044b\u0442\u044c|\u0435\u0441\u0442\u044c \u043b\u0438 \u0443 \u043c\u0435\u043d\u044f)", phrase):
        # Hypotheticals express a question; the previous topic and facts survive.
        result = deepcopy(memory or {"topic": "general", "facts": []})
        result["last_update"] = {"kind": "other", "keys": []}
        return result
    if re.search(r"\u043f\u043e\u0434\u0432\u0435\u0434\u0438 \u0438\u0442\u043e\u0433|\u0441\u0432\u043e\u0434\u043a|\u0440\u0435\u0437\u044e\u043c\u0435|\u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u0432\u0441\u0435|\u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439.*(?:\u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438|\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u0435\u043b|\u043f\u0440\u043e\u0433\u043d\u043e\u0437)|\u043e\u0431\u043e\u0431\u0449\u0438", phrase):
        update["kind"] = "summary"
        return current
    if re.search(r"\u0431\u043e\u043b\u044c\u043d\u043e\s+(?:\u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442|\u043e\u0442\u043f\u0443\u0441\u043a\u0430\u0435\u0442)|(?:\u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442|\u043e\u0442\u043f\u0443\u0441\u043a\u0430\u0435\u0442)\s+\u0431\u043e\u043b\u044c\u043d\u043e", phrase):
        update.update(kind="ambiguous", keys=["pain_course"])
        return current
    if pending:
        update["question"] = deepcopy(q)
    if phrase in YES | NO and not raw.endswith("?"):
        if pending and q["expected"] == "boolean" and targets and (len(targets) == 1 or phrase in NO):
            for key in targets:
                add(key, phrase in YES, "affirmed" if phrase in YES else "denial", True)
        else:
            update.update(kind="ambiguous", keys=list(targets))
            return current
    elif UNCERTAIN.search(phrase) and not statement:
        update["kind"] = "uncertain"
        if len(targets) == 1 and UNCERTAIN.fullmatch(phrase):
            add(targets[0], None, "uncertainty", True)
        return current
    else:
        phrase = statement
        # Preserve explicit polarity. Unmentioned symptoms are absent from
        # the projection (unknown); a question is never evidence of a symptom.
        for key in sorted(codes):
            if key in TARGETS and _denied(phrase, TARGETS[key]):
                continue
            add(key, True, "affirmed")
        site = OTHER_PAIN.search(phrase)
        if site:
            add("reported_pain", site[0], "qualitative")
        if re.search(TARGETS["neck_swelling"], phrase):
            add("neck_swelling", True, "affirmed")
        if topic == "head" and re.search(r"\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*)\b", phrase):
            add("head_impact", True, "affirmed")
        if topic == "bleeding" and re.search(r"\b\u043f\u043e\u0440\u0435\u0437\u0430\u043b\w*", phrase):
            add("cut_site", "\u043f\u0430\u043b\u0435\u0446" if re.search(r"\u043f\u0430\u043b\u0435\u0446|\u043f\u0430\u043b\u044c\u0446", phrase) else "\u0440\u0443\u043a\u0430" if re.search(r"\u0440\u0443\u043a", phrase) else "\u043d\u0435 \u0443\u0442\u043e\u0447\u043d\u0435\u043d\u043e", "qualitative")
        if re.search(r"\b(?:\u043a\u0440\u043e\u0432\u0438\s+(?:\u043f\u043e\u0447\u0442\u0438\s+)?\u043d\u0435\u0442|\u043a\u0440\u043e\u0432\u044c\s+\u043f\u043e\u0447\u0442\u0438\s+\u043d\u0435\s+\u0438\u0434[\u0435\u0451]\u0442)\b", phrase):
            add("bleeding_amount", "\u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442" if "\u043f\u043e\u0447\u0442\u0438" in phrase else "\u043d\u0435\u0442", "qualitative")
        for key, pattern in TARGETS.items():
            if key not in {"vomiting", "nausea", "dizziness", "associated_symptoms", "head_impact", "diarrhea", "weakness", "speech_change"}:
                continue
            if _denied(phrase, pattern):
                add(key, False, "denial")
        scores = list(SCORE.finditer(phrase))
        pain_context = topic in PAIN_TOPICS or topic.startswith("pain_") or "pain_score" in targets or "\u0431\u043e\u043b" in phrase
        unrelated_scale = re.search(r"\u0443\u0441\u0442\u0430\u043b\u043e\u0441\u0442\u044c|\u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d\u0438\u0435|\u043a\u0430\u0447\u0435\u0441\u0442\u0432\u043e \u0441\u043d\u0430|\u0442\u0440\u0435\u0432\u043e\u0433\u0430", phrase)
        if scores and pain_context and not unrelated_scale:
            add("pain_score", int(scores[-1][1]), "numeric")
        elif "pain_score" in targets and re.fullmatch(r"10|[0-9]", phrase):
            add("pain_score", int(phrase), "numeric", True)
        match = TIME.search(phrase)
        if match:
            if "measurement_time" in targets or re.search(r"\u0438\u0437\u043c\u0435\u0440\w*\s*(?:\u0432\s*)?$", phrase[:match.start()]):
                add("measurement_time", match[0], "qualitative")
            elif topic in PAIN_TOPICS:
                near = phrase[max(0, match.start() - 22):match.end() + 32]
                onset_answer = "onset" in targets and len(phrase) <= 26
                if onset_answer or re.search(r"\b(?:\u0431\u043e\u043b\w*|\u043d\u0430\u0447\u0430\u043b\w*|\u043f\u043e\u044f\u0432\u0438\u043b\w*)\b", near):
                    add("onset", match[0], "qualitative")
        if re.search(r"\b\u0438\u0437\u043c\u0435\u0440\w*\s+\u0441\u0435\u0439\u0447\u0430\u0441\b", phrase):
            add("measurement_time", "\u0441\u0435\u0439\u0447\u0430\u0441", "qualitative")
        if topic == "food":
            drink = re.search(r"\b(?:\u043f\u0438\u0442\u044c (?:\u043d\u0435 )?\u043c\u043e\u0433\u0443|(?:\u043d\u0435 )?\u043c\u043e\u0433\u0443 \u043f\u0438\u0442\u044c)\b", phrase)
            if drink:
                able = "\u043d\u0435 " not in drink[0]
                add("fluid_tolerance", able, "affirmed" if able else "denial")
            interval = re.search(r"\b(?:\u0447\u0435\u0440\u0435\u0437|\u0441\u043f\u0443\u0441\u0442\u044f)\s+(?:\d+|\u043e\u0434\u0438\u043d|\u0434\u0432\u0430|\u0442\u0440\u0438|\u0447\u0435\u0442\u044b\u0440\u0435|\u043f\u044f\u0442\u044c|\u0448\u0435\u0441\u0442\u044c)\s+(?:\u0447\u0430\u0441\w*|\u043c\u0438\u043d\u0443\u0442\w*)\b", phrase)
            if interval:
                add("reported_interval", interval[0], "qualitative")
        measured = []
        for clause in re.split(r"[;!?]|\.(?!\d)|,\s+(?!\u0430\b)", phrase):
            if UNCERTAIN.search(clause) or re.search(r"\b(?:\u043c\u043e\u0436\u0435\u0442|\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e|\u043a\u0430\u0436\u0435\u0442\u0441\u044f|\u0435\u0441\u043b\u0438|\u0434\u043e\u043f\u0443\u0441\u0442\u0438\u043c|\u043d\u0430\u043f\u0440\u0438\u043c\u0435\u0440|\u043d\u0430\u0432\u0435\u0440\u043d\u043e\u0435|\u0432\u0440\u044f\u0434 \u043b\u0438)\b", clause):
                continue
            corrected = re.search(r"\b(\u0434\u0430\u0432\u043b\u0435\u043d\u0438[\u0435\u044f]|\u0430\u0434|\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430|\u043f\u0443\u043b\u044c\u0441|\u0441\u0430\u0442\u0443\u0440\u0430\u0446\u0438\u044f)\s+\u043d\u0435\s+[\d/., ]+[, ]\s*\u0430\s+([\d/.,]+)", clause)
            if corrected:
                clause = corrected[1] + " " + corrected[2]
            elif re.search(r"\b(?:\u043d\u0435|\u0431\u0435\u0437|\u043d\u0435\u0442)\b", clause):
                continue
            readings = explicit_measurements(clause)
            if "blood_pressure" in targets and re.match(r"^\s*\d{2,3}\s*/", clause):
                readings.extend(explicit_measurements("\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435 " + clause.strip()))
            measured.extend(readings)
        for m in measured:
            value = [m["systolic"], m["diastolic"]] if m["metric"] == "blood_pressure" else m["scalar_value"]
            add(m["metric"], value, "numeric")
        qualitative = re.search(r"(?:\u0434\u0430\u0432\u043b\u0435\u043d\u0438\w*|\u0430\u0434)\s+((?:\u0447\u0443\u0442\u044c |\u043d\u0435\u043c\u043d\u043e\u0433\u043e )?(?:\u0432\u044b\u0448\u0435|\u043d\u0438\u0436\u0435)(?: \u043d\u043e\u0440\u043c\u044b)?|\u043f\u043e\u0432\u044b\u0448\u0435\u043d\w*|\u043f\u043e\u043d\u0438\u0436\u0435\u043d\w*)", phrase)
        if qualitative and not re.search(r"\b\u043d\u0435\s*$", phrase[:qualitative.start()]):
            add("blood_pressure_description", qualitative[1], "qualitative")
        else:
            desc = re.search(r"\u0438\u0437\u043c\u0435\u0440\w*\s+\u0434\u0430\u0432\u043b\u0435\u043d\u0438\w*[\s,–—:-]+((?:\u0447\u0443\u0442\u044c |\u043d\u0435\u043c\u043d\u043e\u0433\u043e )?(?:\u0432\u044b\u0448\u0435|\u043d\u0438\u0436\u0435) \u043d\u043e\u0440\u043c\u044b)", phrase)
            if desc:
                add("blood_pressure_description", desc[1], "qualitative")
        course = re.search(r"\b(?:\u0431\u043e\u043b\u044c\s+(?:\u043d\u0435\s+)?(?:\u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442|\u0443\u0441\u0438\u043b\u0438\u0432\u0430\u0435\u0442\u0441\u044f|\u0441\u0442\u0438\u0445\u0430\u0435\u0442|\u0434\u0435\u0440\u0436\u0438\u0442\u0441\u044f)|(?:\u0441\u0442\u0430\u043b\u043e|\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u0442\u0441\u044f)\s+(?:\u043b\u0443\u0447\u0448\u0435|\u0445\u0443\u0436\u0435))\b", phrase)
        if course:
            add("pain_course", course[0], "change")
        elif "pain_course" in targets and re.fullmatch(r"(\u043d\u0435\s+)?(\u043f\u0440\u043e\u0445\u043e\u0434\u0438\u0442|\u0434\u0435\u0440\u0436\u0438\u0442\u0441\u044f|\u0441\u0442\u0438\u0445\u0430\u0435\u0442|\u0443\u0441\u0438\u043b\u0438\u0432\u0430\u0435\u0442\u0441\u044f)", phrase):
            add("pain_course", phrase, "change", True)
    answered = set(q.get("answered_targets", [])) | set(update["keys"])
    if pending and targets:
        q["answered_targets"] = [key for key in targets if key in answered]
    if pending and targets and set(targets) <= answered:
        q.update(status="resolved", resolved_by=source)
        if update["kind"] != "correction":
            update["kind"] = "answer"
    elif update["keys"] and update["kind"] == "other":
        update["kind"] = "new_facts"
    # Older superseded values remain reconstructible from the saved transcript.
    inactive = [f for f in facts if f["status"] == "superseded"][-16:]
    current["facts"] = inactive + [f for f in facts if f["status"] == "active"]
    return current
