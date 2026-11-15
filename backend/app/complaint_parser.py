"""Offline extraction of explicit symptoms from English and Russian input."""

import re
from typing import Any


ENGLISH_ALIASES = (
    (r"\b(?:hello|hi|hey)\b", "привет"),
    (r"\b(?:analy[sz]e|review|summari[sz]e)\s+(?:all\s+)?my\s+(?:measurements?|readings?)\s+and\s+forecasts?\b", "проанализируй все мои измерения и прогнозы"),
    (r"\b(?:i have a |i've got a |i have |i've got )?headache\b|\bmy head hurts\b", "болит голова"),
    (r"\b(?:hit|struck|bumped|injured)\s+(?:my\s+)?head\b|\bhead injury\b", "ударил голову"),
    (r"\b(?:stomach|abdomen|belly)\s+(?:hurts|aches)\b|\b(?:abdominal|stomach|belly) pain\b", "болит живот"),
    (r"\b(?:spoiled|bad|stale) food\b|\bfood poisoning\b", "испорченная еда"),
    (r"\b(?:cut|sliced)\s+(?:my\s+)?finger\b", "порезал палец"),
    (r"\b(?:cut|sliced)\s+(?:my\s+)?(?:hand|arm|wrist)\b", "порезал руку"),
    (r"\b(?:bleeding|blood is flowing|blood is spurting)\b", "кровотечение"),
    (r"\b(?:almost no blood|very little blood|hardly any blood)\b", "крови почти нет"),
    (r"\b(?:no blood|not bleeding)\b", "крови нет"),
    (r"\b(?:nausea|nauseous|feel sick)\b", "тошнота"),
    (r"\b(?:vomiting|vomit|throwing up)\b", "рвота"),
    (r"\b(?:dizzy|dizziness|lightheaded)\b", "головокружение"),
    (r"\b(?:diarrhea|diarrhoea)\b", "диарея"),
    (r"\b(?:fever|feverish|feel hot)\b", "жар"),
    (r"\b(?:short of breath|difficulty breathing|breathless)\b", "одышка"),
    (r"\bharder to breathe\b", "одышка"),
    (r"\b(?:loud )?snoring\b", "громкий храп"),
    (r"\b(?:pauses? in breathing|breathing pauses?)\b", "остановки дыхания"),
    (r"\bdaytime sleepiness\b", "дневная сонливость"),
    (r"\bchest pain\b", "болит в груди"),
    (r"\b(?:pain is gone|pain has gone|pain went away|it no longer hurts)\b", "боль прошла"),
    (r"\b(?:no pain or other symptoms|no pain and no other symptoms)\b", "нет боли и других симптомов"),
    (r"\b(?:symptoms are gone|everything is gone)\b", "все прошло"),
    (r"\b(?:i feel fine|i am fine|i'm fine|feeling okay|feeling ok)\b", "чувствую себя нормально"),
    (r"\b(?:an hour ago|one hour ago)\b", "час назад"),
    (r"\b(\d+)\s+(?:minutes?|mins?)\s+ago\b", r"\1 минут назад"),
    (r"\b(\d+)\s+hours?\s+ago\b", r"\1 часов назад"),
    (r"\bthis morning\b", "утром"),
    (r"\b(?:blood pressure|bp)\b", "давление"),
    (r"\b(?:heart rate|pulse)\b", "пульс"),
    (r"\b(?:body temperature|temperature)\b", "температура"),
    (r"\b(?:oxygen saturation|saturation)\b", "сатурация"),
    (r"\b(?:no|none|not any)\s+(?=(?:тошнота|рвота|головокружение|диарея|одышка|кровотечение)\b)", "нет "),
)


def normalize_english(text: str) -> str:
    """Map common English reports to existing Russian extraction vocabulary."""
    normalized = text.casefold()
    if re.fullmatch(r"\s*(?:yes|yeah|yep|no|nope|not sure|i don't know)\s*[.!?]?\s*", normalized):
        return {"yes": "да", "yeah": "да", "yep": "да", "no": "нет", "nope": "нет",
                "not sure": "не знаю", "i don't know": "не знаю"}[normalized.strip(" \t\r\n.!?")]
    for pattern, replacement in ENGLISH_ALIASES:
        normalized = re.sub(pattern, replacement, normalized, flags=re.I)
    normalized = re.sub(
        r"\bнет\s+(тошнота|рвота|головокружение|диарея|одышка)\s+(?:or|and)\s+"
        r"(тошнота|рвота|головокружение|диарея|одышка)\b",
        r"нет \1, нет \2", normalized,
    )
    normalized = re.sub(r"\b(давление|пульс|температура|сатурация)\s+(?:is|reads|was)\s+", r"\1 ", normalized)
    return normalized


SYMPTOM_PATTERNS = {
    "loud_snoring": r"\b(?:громк\w*\s+)?храп\w*\b",
    "witnessed_breathing_pauses": r"\b(?:останов\w*|пауз\w*|перерыв\w*)\s+дыхани\w*\b|\bпереста\w*\s+дышать\b",
    "daytime_sleepiness": r"\b(?:дн[её]м\s+)?сонлив\w*\b|\bхоч\w*\s+спать\s+дн[её]м\b",
    "headache": r"\bголовн\w*\s+бол\w*\b|\bбол\w*\s+голов\w*\b",
    "nausea": r"\bтошн\w*\b|\bподташнив\w*\b",
    "vomiting": r"\bрвот\w*\b|\bрв[её]т\b|\bвырвал\w*\b",
    "external_bleeding": r"\b(?:теч[её]т|ид[её]т|пошла)\s+(?:\w+\s+){0,2}кров\w*\b|\bкров\w*\s+(?:\w+\s+){0,2}(?:теч[её]т|ид[её]т|ль[её]тся|фонтан\w*)\b|\bкровотеч\w*\b|\bкровит\b",
    "dyspnea": r"\bодышк\w*\b|\bтрудно\s+дышать\b",
    "chest_pain": r"\bбол\w*\s+в\s+груд\w*\b",
    "vision_change": r"\bухудш\w*\s+зрени\w*\b|\bзатуман\w*\s+зрени\w*\b",
    "dizziness": r"\bголовокружени\w*\b|\bкруж\w*\s+голов\w*\b",
    "abdominal_pain": r"\bбол\w*\s+живот\w*\b|\bживот\w*\s+бол\w*\b|\bкрут\w*\s+живот\w*\b|\bспазм\w*\s+в\s+живот\w*\b",
    "diarrhea": r"\bдиаре\w*\b|\bпонос\w*\b|\bжидк\w*\s+стул\b",
    "fever": r"\bлихорад\w*\b|\bжар\b|\bповышен\w*\s+температур\w*\b",
}
NEGATION = re.compile(r"\b(?:не|нет|без|отрицаю|отрицает)\b", re.IGNORECASE)
HEAD_IMPACT_PATTERNS = (
    re.compile(r"\b(?:ударил\w*|стукнул\w*|ушиб\w*|травмир\w*)\b[^,.!?;\n]{0,40}\bголов\w*\b"),
    re.compile(r"\bголов\w*\b[^,.!?;\n]{0,40}\b(?:ударил\w*|стукнул\w*|ушиб\w*)\b"),
    re.compile(r"\b(?:травм\w*|ушиб\w*|удар\w*)\s+(?:по\s+)?голов\w*\b"),
)


def _affirmed(text: str, start: int, end: int) -> bool:
    preceding = re.split(r"[.!?;,]", text[max(0, start - 18):start])[-1]
    following = text[end:end + 15]
    return not NEGATION.search(preceding) and not re.match(r"\s*(?:нет\b|не\s+\w+|отсутству\w*)", following)


def _head_impact_reported(text: str) -> bool:
    for pattern in HEAD_IMPACT_PATTERNS:
        if any(_affirmed(text, match.start(), match.end()) for match in pattern.finditer(text)):
            return True
    # A pronoun is linked to a preceding mention of the head in the same report.
    for match in re.finditer(r"\b(?:ударил\w*|стукнул\w*|ушиб\w*)\s+ею\b", text):
        preceding = text[max(0, match.start() - 100):match.start()]
        if re.search(r"\bголов\w*\b", preceding) and _affirmed(text, match.start(), match.end()):
            return True
    # Russian speakers often omit the object after mentioning a painful head.
    if re.search(r"\bголов\w*\b", text):
        for match in re.finditer(r"\b(?:ударил\w*|стукнул\w*|ушиб\w*)\b", text):
            following = text[match.end():match.end() + 18]
            if _affirmed(text, match.start(), match.end()) and not re.match(r"\s+(?:ногой|рукой|локтем|коленом)\b", following):
                return True
    return False


def symptom_codes(description: str) -> list[str]:
    result = []
    text = normalize_english(description)
    for code, pattern in SYMPTOM_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if code == "external_bleeding" and re.search(r"\bне\s+(?:теч[её]т|ид[её]т|ль[её]тся)\b", match.group(0)):
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
    pressure = re.search(r"\b(?:давлени[ея]|ад)\s*[:=]?\s*(\d{2,3})\s*(?:/|на)\s*(\d{2,3})\b", text)
    if pressure:
        systolic, diastolic = map(int, pressure.groups())
        if 50 <= systolic <= 300 and 30 <= diastolic < systolic:
            result.append({"metric": "blood_pressure", "value_kind": "blood_pressure", "systolic": systolic, "diastolic": diastolic, "unit": "mmHg"})
    scalar_patterns = (
        ("heart_rate", r"\b(?:пульс|чсс)\s*[:=]?\s*(\d{2,3})\b", "bpm", 20, 250),
        ("spo2", r"\b(?:сатураци[яи]|spo2|spо2|spo₂|spо₂)\s*[:=]?\s*(\d{2,3})\s*%?", "%", 0, 100),
        ("body_temperature", r"\bтемператур\w*\s*[:=]?\s*(\d{2}(?:[.,]\d)?)", "°C", 30, 45),
        ("sleep_duration", r"\b(?:спал\w*|сон)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*(?:час\w*|ч\b)", "h", 0, 24),
    )
    for metric, pattern, unit, minimum, maximum in scalar_patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1).replace(",", "."))
            if minimum <= value <= maximum:
                result.append({"metric": metric, "value_kind": "scalar", "scalar_value": value, "unit": unit})
    return result
