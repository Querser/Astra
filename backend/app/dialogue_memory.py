"""Profile-scoped conversation state. Only advance() can write user facts.

The database owns the transcript. This projection holds the active episode and
the sources of its facts; starting an unrelated episode resets the projection.
"""
import re
from copy import deepcopy

from app.complaint_parser import explicit_measurements, normalize_english, symptom_codes


TARGETS = {
    "vomiting": r"рвот|рвало|вырвал|vomit|throw up",
    "nausea": r"тошн|nausea",
    "dizziness": r"головокруж|кружится голова|dizz",
    "associated_symptoms": r"сопутствующ|другие симптомы|других симптом|other symptoms|associated symptoms",
    "pain_course": r"проходит|держится|ослабева|усилива|уменьша|нараста|стихает|сохраняется|improv|worsen|still hurt|gone away",
    "pain_score": r"по силе|сильн|интенсивност|шкале|балл|из 10|/10|сил[ау] боли|how severe|pain score|out of 10",
    "onset": r"как давно|когда.{0,24}(?:нач|появ)|нача(?:л|ло)|when.{0,30}(?:start|begin)|how long",
    "blood_pressure": r"давлени|тонометр|два числа",
    "measurement_time": r"когда.{0,45}(?:измер|мерил)|время.{0,10}измер",
    "body_temperature": r"температур",
    "head_impact": r"удар|травм",
    "diarrhea": r"понос|диаре",
    "weakness": r"слабост",
    "speech_change": r"нарушени\w* речи",
    "fluid_tolerance": r"(?:можете|уда[её]тся|получается)\s+(?:ли\s+)?пить",
    "neck_swelling": r"ше[яию]\s+опух|опух\w*\s+ше[яию]|от[её]к\w*\s+ше[яию]",
    "dehydration": r"обезвож|сухост\w*\s+во\s+рту|мочеиспускан",
    "fluid_intake": r"\b(?:пил|пила|пили|выпил\w*|выпила\w*)\b|пил\w*\s+воду",
}
YES = {"да", "есть", "ага"}
NO = {"нет", "нету", "не было", "не наблюдал", "не наблюдала"}
UNCERTAIN = re.compile(r"не знаю|не уверен|не помню|затрудняюсь")
NON_REPORT = re.compile(r"\b(?:если|допустим|например|возможно|наверное|может быть|вряд ли|кажется)\b")
SCORE = re.compile(r"(?<!\d)(10|[0-9])\s*(?:из\s*10|/\s*10|балл\w*)\b")
TIME = re.compile(r"\b(?:с утра|утром|вечером|ночью|полчаса назад|(?:\d+|час|два|три|пять)\s*(?:минут\w*|час\w*)?\s+назад|\d{1,2}:\d{2})\b")
PAIN_TOPICS = {"headache", "fever_headache", "head", "food", "chest_pain"}
OTHER_PAIN = re.compile(r"\b(?:болит|заболел[аи]?)\s+(?P<site>спина|поясница|колено|плечо|нога|рука|шея|ухо|зуб)\b")


def resolved_complaint(text, topic):
    phrase = normalize_english(text).replace("ё", "е")
    if re.search(r"\bвсе\s+прошло\b|\bнет\s+боли\s+и\s+других\s+(?:признаков|симптомов)\b", phrase):
        return True
    if re.search(r"\b(?:боль|голова|симптом\w*)\s+(?:полностью\s+)?прошл\w*|\bбольше\s+не\s+болит\b|\bболи\s+нет\b", phrase):
        return True
    return topic == "food" and bool(re.search(r"\bживот\s+(?:полностью\s+)?прош[её]л\b|\bживот\s+больше\s+не\s+болит\b", phrase))


def _question(text, assistant_id, topic):
    parts = re.findall(r"[^.?!\n]*\?", text)
    if not parts:
        parts = re.findall(r"(?:уточните|скажите|сообщите|напишите|проверь(?:те)?\s*,?\s*не\s+было\s+ли)[^.?!\n]*", text, re.I)[-1:]
    if not parts:
        return None
    wording = " ".join(part.strip() for part in parts)[-400:]
    lower = normalize_english(wording)
    targets = [key for key, pattern in TARGETS.items() if re.search(pattern, lower)]
    # "Do you have nausea or vomiting?" is a yes/no symptom screen. An answer
    # to "Is it improving or persisting?" must instead specify an alternative.
    polar = bool(re.search(r"\b(есть ли|был[аио]? ли|не было ли|наблюда\w* ли|быва\w* ли|можете ли|уда[её]тся ли|ты уже пил|вы уже пили|пил[аи]? ли|вас тошнит|тошнит|рвота есть|have you|do you|did you|are you|is there|any)\b", lower))
    expected = "open"
    if (" или " in lower or " or " in lower) and not polar:
        expected = "choice"
    elif polar and not re.search(r"\b(?:сколько|когда|насколько|какие|how many|how long|when|which)\b", lower):
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
    if previous in {"fever", "fever_headache"} and re.search(r"\b(?:писал|говорил|только что|не думаю|выполняю действия)\b", text) and re.search(r"порез|кровотеч", text):
        return previous
    if "head_impact" in codes:
        return "head"
    if previous in {"headache", "head"} and re.search(r"\b(?:ударил\w*|стукнул\w*|ушиб\w*)\b", text):
        return "head"
    if "external_bleeding" in codes or re.search(r"\bпорезал\w*", text):
        return "bleeding"
    if "headache" in codes or re.search(r"голова болит|разболелась голова", text):
        return "fever_headache" if "fever" in codes else "headache"
    if "abdominal_pain" in codes or re.search(r"живот.{0,12}(?:крутит|болит)", text):
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
    if re.search(r"сатурац|spo[2₂]", text):
        return "oxygen"
    if re.search(r"давлени|тонометр", text) and (previous == "general" or "другая" in text):
        return "blood_pressure"
    return previous


def _denied(text, pattern):
    """Scope an explicit negative to a symptom or a coordinated symptom list."""
    for clause in re.split(r"[.,;!?]|\s+(?:но|а)\s+|\s+и\s+(?=(?:есть|нет|без)\b)", text):
        for match in re.finditer(pattern, clause):
            before, after = clause[:match.start()], clause[match.end():]
            if re.search(r"\bне\s+$", before) and re.match(r"(?:рвало|вырвал|тошн|кружится)", match[0]):
                return True
            if re.search(r"\b(?:без|нет|не было|отсутствуют)\s+(?:\w+\s+и\s+)?$", before):
                return True
            if re.match(r"\w*\s+(?:и\s+\w+\s+)?(?:нет|не было|отсутству\w*)\b", after):
                return True
    return False


def advance(memory, user_message_id, text):
    current = deepcopy(memory or {})
    if current.get("episode_resolved") and symptom_codes(text):
        current = {"medical_history": current.get("medical_history", [])}
    previous = current.get("topic", "general")
    q = current.get("open_question") or {}
    pending = q.get("status") == "unresolved"
    raw = normalize_english(text).replace("ё", "е").replace("темпиратур", "температур").strip()
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
            if prior["value"] != value and re.search(r"поправ|уточн|ошиб|точнее|перепут|не .+[, ]а ", phrase):
                update["kind"] = "correction"
        fact = {"key": key, "value": value, "kind": kind, "user_message_id": source, "status": "active"}
        if pending and (linked or key in targets):
            fact["question_id"] = q["assistant_message_id"]
        facts.append(fact)
        update["keys"].append(key)

    resolved = resolved_complaint(text, topic)
    neck_still_swollen = any(f.get("key") == "neck_swelling" and f.get("value") is True and f.get("status") == "active" for f in facts)
    complete = bool(re.search(r"вс[её]\s+прошло|от[её]к\s+шеи\s+прош[её]л|шея\s+больше\s+не\s+опух", text, re.I))
    if resolved:
        was_resolved = bool(current.get("episode_resolved"))
        update["kind"] = ("partial_resolution" if neck_still_swollen and not complete else
                          "resolution_confirmed" if was_resolved else "resolution")
        current["episode_resolved"] = update["kind"] != "partial_resolution"
        if topic == "food":
            add("abdominal_pain", False, "denial")
        elif topic in {"headache", "head", "fever_headache"}:
            add("headache", False, "denial")
        add("pain_course", "прошла", "change")
        if pending:
            q.update(status="resolved", resolved_by=source)
        current["open_question"] = q
        return current

    if phrase in {"привет", "здравствуйте", "добрый день"}:
        update["kind"] = "greeting"
        return current
    if "?" in text and re.match(r"(может ли|а если|что если|а вдруг|может быть|есть ли у меня)", phrase):
        # Hypotheticals express a question; the previous topic and facts survive.
        result = deepcopy(memory or {"topic": "general", "facts": []})
        result["last_update"] = {"kind": "other", "keys": []}
        return result
    if re.search(r"подведи итог|сводк|резюме|проанализируй все|проанализируй.*(?:измерени|показател|прогноз)|обобщи", phrase):
        update["kind"] = "summary"
        return current
    if re.search(r"больно\s+(?:проходит|отпускает)|(?:проходит|отпускает)\s+больно", phrase):
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
        if topic == "head" and re.search(r"\b(?:ударил\w*|стукнул\w*|ушиб\w*)\b", phrase):
            add("head_impact", True, "affirmed")
        if topic == "bleeding" and re.search(r"\bпорезал\w*", phrase):
            add("cut_site", "палец" if re.search(r"палец|пальц", phrase) else "рука" if re.search(r"рук", phrase) else "не уточнено", "qualitative")
        if re.search(r"\b(?:крови\s+(?:почти\s+)?нет|кровь\s+почти\s+не\s+ид[её]т)\b", phrase):
            add("bleeding_amount", "почти нет" if "почти" in phrase else "нет", "qualitative")
        for key, pattern in TARGETS.items():
            if key not in {"vomiting", "nausea", "dizziness", "associated_symptoms", "head_impact", "diarrhea", "weakness", "speech_change"}:
                continue
            if _denied(phrase, pattern):
                add(key, False, "denial")
        scores = list(SCORE.finditer(phrase))
        pain_context = topic in PAIN_TOPICS or topic.startswith("pain_") or "pain_score" in targets or "бол" in phrase
        unrelated_scale = re.search(r"усталость|настроение|качество сна|тревога", phrase)
        if scores and pain_context and not unrelated_scale:
            add("pain_score", int(scores[-1][1]), "numeric")
        elif "pain_score" in targets and re.fullmatch(r"10|[0-9]", phrase):
            add("pain_score", int(phrase), "numeric", True)
        match = TIME.search(phrase)
        if match:
            if "measurement_time" in targets or re.search(r"измер\w*\s*(?:в\s*)?$", phrase[:match.start()]):
                add("measurement_time", match[0], "qualitative")
            elif topic in PAIN_TOPICS:
                near = phrase[max(0, match.start() - 22):match.end() + 32]
                onset_answer = "onset" in targets and len(phrase) <= 26
                if onset_answer or re.search(r"\b(?:бол\w*|начал\w*|появил\w*)\b", near):
                    add("onset", match[0], "qualitative")
        if re.search(r"\bизмер\w*\s+сейчас\b", phrase):
            add("measurement_time", "сейчас", "qualitative")
        if topic == "food":
            drink = re.search(r"\b(?:пить (?:не )?могу|(?:не )?могу пить)\b", phrase)
            if drink:
                able = "не " not in drink[0]
                add("fluid_tolerance", able, "affirmed" if able else "denial")
            interval = re.search(r"\b(?:через|спустя)\s+(?:\d+|один|два|три|четыре|пять|шесть)\s+(?:час\w*|минут\w*)\b", phrase)
            if interval:
                add("reported_interval", interval[0], "qualitative")
        measured = []
        for clause in re.split(r"[;!?]|\.(?!\d)|,\s+(?!а\b)", phrase):
            if UNCERTAIN.search(clause) or re.search(r"\b(?:может|возможно|кажется|если|допустим|например|наверное|вряд ли)\b", clause):
                continue
            corrected = re.search(r"\b(давлени[ея]|ад|температура|пульс|сатурация)\s+не\s+[\d/., ]+[, ]\s*а\s+([\d/.,]+)", clause)
            if corrected:
                clause = corrected[1] + " " + corrected[2]
            elif re.search(r"\b(?:не|без|нет)\b", clause):
                continue
            readings = explicit_measurements(clause)
            if "blood_pressure" in targets and re.match(r"^\s*\d{2,3}\s*/", clause):
                readings.extend(explicit_measurements("давление " + clause.strip()))
            measured.extend(readings)
        for m in measured:
            value = [m["systolic"], m["diastolic"]] if m["metric"] == "blood_pressure" else m["scalar_value"]
            add(m["metric"], value, "numeric")
        qualitative = re.search(r"(?:давлени\w*|ад)\s+((?:чуть |немного )?(?:выше|ниже)(?: нормы)?|повышен\w*|понижен\w*)", phrase)
        if qualitative and not re.search(r"\bне\s*$", phrase[:qualitative.start()]):
            add("blood_pressure_description", qualitative[1], "qualitative")
        else:
            desc = re.search(r"измер\w*\s+давлени\w*[\s,–—:-]+((?:чуть |немного )?(?:выше|ниже) нормы)", phrase)
            if desc:
                add("blood_pressure_description", desc[1], "qualitative")
        course = re.search(r"\b(?:боль\s+(?:не\s+)?(?:проходит|усиливается|стихает|держится)|(?:стало|становится)\s+(?:лучше|хуже))\b", phrase)
        if course:
            add("pain_course", course[0], "change")
        elif "pain_course" in targets and re.fullmatch(r"(не\s+)?(проходит|держится|стихает|усиливается)", phrase):
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
