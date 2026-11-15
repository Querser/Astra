"""Offline extraction of explicit symptoms from English and Russian input."""

import re
from typing import Any


ENGLISH_ALIASES = (
    (r"\b(?:hello|hi|hey)\b", "\u043f\u0440\u0438\u0432\u0435\u0442"),
    (r"\b(?:analy[sz]e|review|summari[sz]e)\s+(?:all\s+)?my\s+(?:measurements?|readings?)\s+and\s+forecasts?\b", "\u043f\u0440\u043e\u0430\u043d\u0430\u043b\u0438\u0437\u0438\u0440\u0443\u0439 \u0432\u0441\u0435 \u043c\u043e\u0438 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f \u0438 \u043f\u0440\u043e\u0433\u043d\u043e\u0437\u044b"),
    (r"\b(?:i have a |i've got a |i have |i've got )?headache\b|\bmy head hurts\b", "\u0431\u043e\u043b\u0438\u0442 \u0433\u043e\u043b\u043e\u0432\u0430"),
    (r"\b(?:hit|struck|bumped|injured)\s+(?:my\s+)?head\b|\bhead injury\b", "\u0443\u0434\u0430\u0440\u0438\u043b \u0433\u043e\u043b\u043e\u0432\u0443"),
    (r"\b(?:stomach|abdomen|belly)\s+(?:hurts|aches)\b|\b(?:abdominal|stomach|belly) pain\b", "\u0431\u043e\u043b\u0438\u0442 \u0436\u0438\u0432\u043e\u0442"),
    (r"\b(?:spoiled|bad|stale) food\b|\bfood poisoning\b", "\u0438\u0441\u043f\u043e\u0440\u0447\u0435\u043d\u043d\u0430\u044f \u0435\u0434\u0430"),
    (r"\b(?:cut|sliced)\s+(?:my\s+)?finger\b", "\u043f\u043e\u0440\u0435\u0437\u0430\u043b \u043f\u0430\u043b\u0435\u0446"),
    (r"\b(?:cut|sliced)\s+(?:my\s+)?(?:hand|arm|wrist)\b", "\u043f\u043e\u0440\u0435\u0437\u0430\u043b \u0440\u0443\u043a\u0443"),
    (r"\b(?:bleeding|blood is flowing|blood is spurting)\b", "\u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\u0435\u043d\u0438\u0435"),
    (r"\b(?:almost no blood|very little blood|hardly any blood)\b", "\u043a\u0440\u043e\u0432\u0438 \u043f\u043e\u0447\u0442\u0438 \u043d\u0435\u0442"),
    (r"\b(?:no blood|not bleeding)\b", "\u043a\u0440\u043e\u0432\u0438 \u043d\u0435\u0442"),
    (r"\b(?:nausea|nauseous|feel sick)\b", "\u0442\u043e\u0448\u043d\u043e\u0442\u0430"),
    (r"\b(?:vomiting|vomit|throwing up)\b", "\u0440\u0432\u043e\u0442\u0430"),
    (r"\b(?:dizzy|dizziness|lightheaded)\b", "\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0435"),
    (r"\b(?:diarrhea|diarrhoea)\b", "\u0434\u0438\u0430\u0440\u0435\u044f"),
    (r"\b(?:fever|feverish|feel hot)\b", "\u0436\u0430\u0440"),
    (r"\b(?:short of breath|difficulty breathing|breathless)\b", "\u043e\u0434\u044b\u0448\u043a\u0430"),
    (r"\bharder to breathe\b", "\u043e\u0434\u044b\u0448\u043a\u0430"),
    (r"\b(?:loud )?snoring\b", "\u0433\u0440\u043e\u043c\u043a\u0438\u0439 \u0445\u0440\u0430\u043f"),
    (r"\b(?:pauses? in breathing|breathing pauses?)\b", "\u043e\u0441\u0442\u0430\u043d\u043e\u0432\u043a\u0438 \u0434\u044b\u0445\u0430\u043d\u0438\u044f"),
    (r"\bdaytime sleepiness\b", "\u0434\u043d\u0435\u0432\u043d\u0430\u044f \u0441\u043e\u043d\u043b\u0438\u0432\u043e\u0441\u0442\u044c"),
    (r"\bchest pain\b", "\u0431\u043e\u043b\u0438\u0442 \u0432 \u0433\u0440\u0443\u0434\u0438"),
    (r"\b(?:pain is gone|pain has gone|pain went away|it no longer hurts)\b", "\u0431\u043e\u043b\u044c \u043f\u0440\u043e\u0448\u043b\u0430"),
    (r"\b(?:no pain or other symptoms|no pain and no other symptoms)\b", "\u043d\u0435\u0442 \u0431\u043e\u043b\u0438 \u0438 \u0434\u0440\u0443\u0433\u0438\u0445 \u0441\u0438\u043c\u043f\u0442\u043e\u043c\u043e\u0432"),
    (r"\b(?:symptoms are gone|everything is gone)\b", "\u0432\u0441\u0435 \u043f\u0440\u043e\u0448\u043b\u043e"),
    (r"\b(?:i feel fine|i am fine|i'm fine|feeling okay|feeling ok)\b", "\u0447\u0443\u0432\u0441\u0442\u0432\u0443\u044e \u0441\u0435\u0431\u044f \u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u043e"),
    (r"\b(?:an hour ago|one hour ago)\b", "\u0447\u0430\u0441 \u043d\u0430\u0437\u0430\u0434"),
    (r"\b(\d+)\s+(?:minutes?|mins?)\s+ago\b", "\\1 \u043c\u0438\u043d\u0443\u0442 \u043d\u0430\u0437\u0430\u0434"),
    (r"\b(\d+)\s+hours?\s+ago\b", "\\1 \u0447\u0430\u0441\u043e\u0432 \u043d\u0430\u0437\u0430\u0434"),
    (r"\bthis morning\b", "\u0443\u0442\u0440\u043e\u043c"),
    (r"\b(?:blood pressure|bp)\b", "\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435"),
    (r"\b(?:heart rate|pulse)\b", "\u043f\u0443\u043b\u044c\u0441"),
    (r"\b(?:body temperature|temperature)\b", "\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430"),
    (r"\b(?:oxygen saturation|saturation)\b", "\u0441\u0430\u0442\u0443\u0440\u0430\u0446\u0438\u044f"),
    (r"\b(?:no|none|not any)\s+(?=(?:\u0442\u043e\u0448\u043d\u043e\u0442\u0430|\u0440\u0432\u043e\u0442\u0430|\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0435|\u0434\u0438\u0430\u0440\u0435\u044f|\u043e\u0434\u044b\u0448\u043a\u0430|\u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\u0435\u043d\u0438\u0435)\b)", "\u043d\u0435\u0442 "),
)


def normalize_english(text: str) -> str:
    """Map common English reports to existing Russian extraction vocabulary."""
    normalized = text.casefold()
    if re.fullmatch(r"\s*(?:yes|yeah|yep|no|nope|not sure|i don't know)\s*[.!?]?\s*", normalized):
        return {"yes": "\u0434\u0430", "yeah": "\u0434\u0430", "yep": "\u0434\u0430", "no": "\u043d\u0435\u0442", "nope": "\u043d\u0435\u0442",
                "not sure": "\u043d\u0435 \u0437\u043d\u0430\u044e", "i don't know": "\u043d\u0435 \u0437\u043d\u0430\u044e"}[normalized.strip(" \t\r\n.!?")]
    for pattern, replacement in ENGLISH_ALIASES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.I)
    normalized = re.sub(
        r"\b\u043d\u0435\u0442\s+(\u0442\u043e\u0448\u043d\u043e\u0442\u0430|\u0440\u0432\u043e\u0442\u0430|\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0435|\u0434\u0438\u0430\u0440\u0435\u044f|\u043e\u0434\u044b\u0448\u043a\u0430)\s+(?:or|and)\s+"
        r"(\u0442\u043e\u0448\u043d\u043e\u0442\u0430|\u0440\u0432\u043e\u0442\u0430|\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\u0435|\u0434\u0438\u0430\u0440\u0435\u044f|\u043e\u0434\u044b\u0448\u043a\u0430)\b",
        "\u043d\u0435\u0442 \\1, \u043d\u0435\u0442 \\2", normalized,
    )
    normalized = re.sub(r"\b(\u0434\u0430\u0432\u043b\u0435\u043d\u0438\u0435|\u043f\u0443\u043b\u044c\u0441|\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\u0430|\u0441\u0430\u0442\u0443\u0440\u0430\u0446\u0438\u044f)\s+(?:is|reads|was)\s+", r"\1 ", normalized)
    return normalized


SYMPTOM_PATTERNS = {
    "loud_snoring": r"\b(?:\u0433\u0440\u043e\u043c\u043a\w*\s+)?\u0445\u0440\u0430\u043f\w*\b",
    "witnessed_breathing_pauses": r"\b(?:\u043e\u0441\u0442\u0430\u043d\u043e\u0432\w*|\u043f\u0430\u0443\u0437\w*|\u043f\u0435\u0440\u0435\u0440\u044b\u0432\w*)\s+\u0434\u044b\u0445\u0430\u043d\u0438\w*\b|\b\u043f\u0435\u0440\u0435\u0441\u0442\u0430\w*\s+\u0434\u044b\u0448\u0430\u0442\u044c\b",
    "daytime_sleepiness": r"\b(?:\u0434\u043d[\u0435\u0451]\u043c\s+)?\u0441\u043e\u043d\u043b\u0438\u0432\w*\b|\b\u0445\u043e\u0447\w*\s+\u0441\u043f\u0430\u0442\u044c\s+\u0434\u043d[\u0435\u0451]\u043c\b",
    "headache": r"\b\u0433\u043e\u043b\u043e\u0432\u043d\w*\s+\u0431\u043e\u043b\w*\b|\b\u0431\u043e\u043b\w*\s+\u0433\u043e\u043b\u043e\u0432\w*\b",
    "nausea": r"\b\u0442\u043e\u0448\u043d\w*\b|\b\u043f\u043e\u0434\u0442\u0430\u0448\u043d\u0438\u0432\w*\b",
    "vomiting": r"\b\u0440\u0432\u043e\u0442\w*\b|\b\u0440\u0432[\u0435\u0451]\u0442\b|\b\u0432\u044b\u0440\u0432\u0430\u043b\w*\b",
    "external_bleeding": r"\b(?:\u0442\u0435\u0447[\u0435\u0451]\u0442|\u0438\u0434[\u0435\u0451]\u0442|\u043f\u043e\u0448\u043b\u0430)\s+(?:\w+\s+){0,2}\u043a\u0440\u043e\u0432\w*\b|\b\u043a\u0440\u043e\u0432\w*\s+(?:\w+\s+){0,2}(?:\u0442\u0435\u0447[\u0435\u0451]\u0442|\u0438\u0434[\u0435\u0451]\u0442|\u043b\u044c[\u0435\u0451]\u0442\u0441\u044f|\u0444\u043e\u043d\u0442\u0430\u043d\w*)\b|\b\u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\w*\b|\b\u043a\u0440\u043e\u0432\u0438\u0442\b",
    "dyspnea": r"\b\u043e\u0434\u044b\u0448\u043a\w*\b|\b\u0442\u0440\u0443\u0434\u043d\u043e\s+\u0434\u044b\u0448\u0430\u0442\u044c\b",
    "chest_pain": r"\b\u0431\u043e\u043b\w*\s+\u0432\s+\u0433\u0440\u0443\u0434\w*\b",
    "vision_change": r"\b\u0443\u0445\u0443\u0434\u0448\w*\s+\u0437\u0440\u0435\u043d\u0438\w*\b|\b\u0437\u0430\u0442\u0443\u043c\u0430\u043d\w*\s+\u0437\u0440\u0435\u043d\u0438\w*\b",
    "dizziness": r"\b\u0433\u043e\u043b\u043e\u0432\u043e\u043a\u0440\u0443\u0436\u0435\u043d\u0438\w*\b|\b\u043a\u0440\u0443\u0436\w*\s+\u0433\u043e\u043b\u043e\u0432\w*\b",
    "abdominal_pain": r"\b\u0431\u043e\u043b\w*\s+\u0436\u0438\u0432\u043e\u0442\w*\b|\b\u0436\u0438\u0432\u043e\u0442\w*\s+\u0431\u043e\u043b\w*\b|\b\u043a\u0440\u0443\u0442\w*\s+\u0436\u0438\u0432\u043e\u0442\w*\b|\b\u0441\u043f\u0430\u0437\u043c\w*\s+\u0432\s+\u0436\u0438\u0432\u043e\u0442\w*\b",
    "diarrhea": r"\b\u0434\u0438\u0430\u0440\u0435\w*\b|\b\u043f\u043e\u043d\u043e\u0441\w*\b|\b\u0436\u0438\u0434\u043a\w*\s+\u0441\u0442\u0443\u043b\b",
    "fever": r"\b\u043b\u0438\u0445\u043e\u0440\u0430\u0434\w*\b|\b\u0436\u0430\u0440\b|\b\u043f\u043e\u0432\u044b\u0448\u0435\u043d\w*\s+\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\w*\b",
}
NEGATION = re.compile(r"\b(?:\u043d\u0435|\u043d\u0435\u0442|\u0431\u0435\u0437|\u043e\u0442\u0440\u0438\u0446\u0430\u044e|\u043e\u0442\u0440\u0438\u0446\u0430\u0435\u0442)\b", re.IGNORECASE)
HEAD_IMPACT_PATTERNS = (
    re.compile(r"\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*|\u0442\u0440\u0430\u0432\u043c\u0438\u0440\w*)\b[^,.!?;\n]{0,40}\b\u0433\u043e\u043b\u043e\u0432\w*\b"),
    re.compile(r"\b\u0433\u043e\u043b\u043e\u0432\w*\b[^,.!?;\n]{0,40}\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*)\b"),
    re.compile(r"\b(?:\u0442\u0440\u0430\u0432\u043c\w*|\u0443\u0448\u0438\u0431\w*|\u0443\u0434\u0430\u0440\w*)\s+(?:\u043f\u043e\s+)?\u0433\u043e\u043b\u043e\u0432\w*\b"),
)


def _affirmed(text: str, start: int, end: int) -> bool:
    preceding = re.split(r"[.!?;,]", text[max(0, start - 18):start])[-1]
    following = text[end:end + 15]
    return not NEGATION.search(preceding) and not re.match(r"\s*(?:\u043d\u0435\u0442\b|\u043d\u0435\s+\w+|\u043e\u0442\u0441\u0443\u0442\u0441\u0442\u0432\u0443\w*)", following)


def _head_impact_reported(text: str) -> bool:
    for pattern in HEAD_IMPACT_PATTERNS:
        if any(_affirmed(text, match.start(), match.end()) for match in pattern.finditer(text)):
            return True
    # A pronoun is linked to a preceding mention of the head in the same report.
    for match in re.finditer(r"\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*)\s+\u0435\u044e\b", text):
        preceding = text[max(0, match.start() - 100):match.start()]
        if re.search(r"\b\u0433\u043e\u043b\u043e\u0432\w*\b", preceding) and _affirmed(text, match.start(), match.end()):
            return True
    # Russian speakers often omit the object after mentioning a painful head.
    if re.search(r"\b\u0433\u043e\u043b\u043e\u0432\w*\b", text):
        for match in re.finditer(r"\b(?:\u0443\u0434\u0430\u0440\u0438\u043b\w*|\u0441\u0442\u0443\u043a\u043d\u0443\u043b\w*|\u0443\u0448\u0438\u0431\w*)\b", text):
            following = text[match.end():match.end() + 18]
            if _affirmed(text, match.start(), match.end()) and not re.match(r"\s+(?:\u043d\u043e\u0433\u043e\u0439|\u0440\u0443\u043a\u043e\u0439|\u043b\u043e\u043a\u0442\u0435\u043c|\u043a\u043e\u043b\u0435\u043d\u043e\u043c)\b", following):
                return True
    return False


def symptom_codes(description: str) -> list[str]:
    result = []
    text = normalize_english(description)
    for code, pattern in SYMPTOM_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if code == "external_bleeding" and re.search(r"\b\u043d\u0435\s+(?:\u0442\u0435\u0447[\u0435\u0451]\u0442|\u0438\u0434[\u0435\u0451]\u0442|\u043b\u044c[\u0435\u0451]\u0442\u0441\u044f)\b", match.group(0)):
                continue
            if _affirmed(text, match.start(), match.end()):
                result.append(code)
                break
    if _head_impact_reported(text):
        result.append("head_impact")
    return result


def explicit_measurements(description: str) -> list[dict[str, Any]]:
    """Extract only clearly labeled numbers; ignore unspecified numbers and prose."""
    text = normalize_english(description)
    result: list[dict[str, Any]] = []
    pressure = re.search(r"\b(?:\u0434\u0430\u0432\u043b\u0435\u043d\u0438[\u0435\u044f]|\u0430\u0434)\s*[:=]?\s*(\d{2,3})\s*(?:/|\u043d\u0430)\s*(\d{2,3})\b", text)
    if pressure:
        systolic, diastolic = map(int, pressure.groups())
        if 50 <= systolic <= 300 and 30 <= diastolic < systolic:
            result.append({"metric": "blood_pressure", "value_kind": "blood_pressure", "systolic": systolic, "diastolic": diastolic, "unit": "mmHg"})
    scalar_patterns = (
        ("heart_rate", r"\b(?:\u043f\u0443\u043b\u044c\u0441|\u0447\u0441\u0441)\s*[:=]?\s*(\d{2,3})\b", "bpm", 20, 250),
        ("spo2", r"\b(?:\u0441\u0430\u0442\u0443\u0440\u0430\u0446\u0438[\u044f\u0438]|spo2|sp\u043e2|spo₂|sp\u043e₂)\s*[:=]?\s*(\d{2,3})\s*%?", "%", 0, 100),
        ("body_temperature", r"\b\u0442\u0435\u043c\u043f\u0435\u0440\u0430\u0442\u0443\u0440\w*\s*[:=]?\s*(\d{2}(?:[.,]\d)?)", "°C", 30, 45),
        ("sleep_duration", r"\b(?:\u0441\u043f\u0430\u043b\w*|\u0441\u043e\u043d)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:\u0447\u0430\u0441\w*|\u0447\b)", "h", 0, 24),
    )
    for metric, pattern, unit, minimum, maximum in scalar_patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1).replace(",", "."))
            if minimum <= value <= maximum:
                result.append({"metric": metric, "value_kind": "scalar", "scalar_value": value, "unit": unit})
    return result
