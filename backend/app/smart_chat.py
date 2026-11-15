"""Offline conversation episodes, local-model fact extraction and sourced replies."""

import json
import logging
import os
import re
from contextvars import ContextVar
from urllib.error import HTTPError
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.request import Request
from uuid import uuid4

from app.assistant import is_loopback_ollama_url, urlopen
from app.chat_engine import reply_to_message
from app.complaint_parser import normalize_english, symptom_codes
from app.dialogue_memory import resolved_complaint
from app.chat_turn import INPUT_BUDGET, NUM_CTX, NUM_PREDICT, nbytes, prepare, validate
from app.models import Observation

logger = logging.getLogger("astra.diagnostics")


SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string", "enum": ["food", "head", "fever_headache", "oxygen", "other"]},
        "head_impact": {"type": "boolean"},
        "spoiled_food": {"type": "boolean"},
        "abdominal_pain": {"type": "boolean"},
        "headache": {"type": "boolean"},
        "dizziness": {"type": "boolean"},
        "nausea": {"type": "boolean"},
        "vomiting": {"type": "boolean"},
        "diarrhea": {"type": "boolean"},
        "bleeding": {"type": "boolean"},
        "severity_0_10": {"type": ["integer", "null"]},
        "food_to_symptoms_hours": {"type": ["number", "null"]},
        "explicitly_no_other_symptoms": {"type": "boolean"}
    },
    "required": ["topic", "head_impact", "spoiled_food", "abdominal_pain", "headache", "dizziness", "nausea", "vomiting", "diarrhea", "bleeding", "severity_0_10", "food_to_symptoms_hours", "explicitly_no_other_symptoms"],
    "additionalProperties": False,
}

@lru_cache(maxsize=1)
def cases() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "reference_docs" / "ASTRA_CHAT_CASES.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def explicit_topic(message: str) -> str | None:
    text = message.casefold()
    codes = set(symptom_codes(text))
    if ("external_bleeding" in codes or re.search(r"\b(?:кров\w*\s+(?:бь[её]т|хлещ\w*|фонтан\w*)|кровотеч\w*|порез\w*|ран\w*)\b", text)):
        return "bleeding"
    if "head_impact" in codes:
        return "head"
    if "headache" in codes and "fever" in codes:
        return "fever_headache"
    if "headache" in codes:
        return "headache"
    if "abdominal_pain" in codes or (re.search(r"\b(?:тухл\w*|испорч\w*|прокисш\w*)\b", text) and re.search(r"\b(?:ел|съел|ела|съела|поел\w*)\b", text)):
        return "food"
    if any(token in text for token in ("spo2", "spo₂", "сатурац")):
        return "oxygen"
    return None


def current_episode(messages: list[str]) -> tuple[str | None, list[str]]:
    """A new explicit complaint starts a new episode; short replies attach to it."""
    if not messages:
        return None, []
    topics = [explicit_topic(item) for item in messages]
    topic = next((item for item in reversed(topics) if item), None)
    if topic is None:
        return None, messages[-3:]
    anchor = max(index for index, item in enumerate(topics) if item == topic)
    # Include earlier turns of the same complaint, but never cross another topic.
    while anchor > 0 and topics[anchor - 1] in {None, topic}:
        if resolved_complaint(messages[anchor - 1], topic):
            break
        anchor -= 1
    return topic, messages[anchor:]


class LocalChatModel:
    """Model-authored answers using only local case files and profile data."""

    def __init__(self, *, enabled: bool | None = None, base_url: str | None = None, model: str | None = None):
        self.enabled = (os.getenv("ASTRA_CHAT_MODEL_ENABLED", "1") != "0") if enabled is None else enabled
        self.base_url = (base_url or os.getenv("ASTRA_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
        self.model = model or os.getenv("ASTRA_OLLAMA_MODEL", "qwen3:8b")
        self._error = ContextVar("astra_chat_error", default=None)

    @property
    def last_validation_error(self) -> str | None:
        return self._error.get()

    def generate(self, episode: list[str], conversation: list[dict[str, str]],
                 observations: list[Observation], analysis: dict[str, Any], topic: str | None,
                 *, memory=None, request_id=None) -> dict[str, Any] | None:
        self._error.set(None)
        if not self.enabled or not is_loopback_ollama_url(self.base_url):
            self._error.set("configuration")
            return None
        previous = next((row["content"] for row in reversed(conversation)
                         if row.get("role") == "assistant" and not str(row.get("engine", "")).startswith("local_model_error:")), "")
        pressure_note = next((f["user_message_id"] for f in (memory or {}).get("facts", [])
                              if f.get("key") == "blood_pressure_description" and f.get("status") == "active"), None)
        start = next((i for i, row in enumerate(conversation) if row.get("id") == pressure_note and pressure_note), None)
        bp_requested = start is not None and any(
            row.get("role") == "assistant" and not str(row.get("engine", "")).startswith("local_model_error:")
            and re.search(r"(?:тонометр|числ[ао]|цифр[ыау]|blood pressure monitor|two numbers|readings?).{0,80}\?", row["content"], re.I)
            for row in conversation[start + 1:]
        )
        previous_research = next((ref for row in reversed(conversation) if row.get("role") == "assistant"
                                  for ref in (row.get("citations") or []) if str(ref).startswith("research:")), None)
        research_focus = ("radlab" if previous_research and "radlab" in previous_research.casefold()
                          else "osd-575" if previous_research and "osd-575" in previous_research.casefold()
                          else None)
        if research_focus is None:
            recent_user = " ".join(str(row.get("content", "")) for row in conversation[-8:]
                                   if row.get("role") == "user").casefold()
            if ("radlab" in recent_user or
                    re.search(r"радиац\w*.{0,50}(?:данн|измер|запис|покаж|окружающ)|"
                              r"(?:данн|измер|запис|покаж).{0,50}радиац|"
                              r"radiation.{0,50}(?:data|readings?|measurements?|records?|show)|"
                              r"(?:data|readings?|measurements?|records?|show).{0,50}radiation", recent_user)):
                research_focus = "radlab"
            elif re.search(r"osd[- ]?575|лаборатор\w*.{0,30}(?:данн|исслед|проб)|laboratory.{0,30}(?:data|study|sample)", recent_user):
                research_focus = "osd-575"
        turn = prepare(episode[-1], previous, memory, topic, observations, analysis,
                       bp_requested=bp_requested, research_focus=research_focus)
        # Keep the nearby exchange in order. The structured fact projection is
        # deliberately sparse and cannot represent actions such as applying ice
        # or a plain-language response such as "I feel fine" by itself.
        episode_start = next((i for i in range(len(conversation) - 1, -1, -1)
                              if conversation[i].get("role") == "user" and
                              conversation[i].get("content") == episode[0]), 0)
        nearby = [(row.get("role"), str(row.get("content", ""))) for row in conversation[episode_start:-1]
                  if row.get("role") in {"user", "assistant"}]
        turn.history_user = [body for role, body in nearby if role == "user"]
        recent = "\n".join(("User" if role == "user" else "Assistant") + ": " + body[:230]
                           for role, body in nearby[-8:])
        if recent and turn.move != "summary":
            turn.required += "\nRecent dialogue (keep context, do not repeat already asked question):\n" + recent[:1500]
        if turn.topic == "food":
            delay = _known_facts([turn.latest])["delay_hours"]
            if delay is not None:
                elapsed = f"\n{delay:g} hours after eating"
                turn.user_facts.append(elapsed)
                turn.required += f"\nUser-specified interval: {elapsed}."
                if turn.move == "open":
                    turn.required += f" Start with the phrase: Possible food poisoning: cramps started {elapsed}."
        if turn.topic == "head" and (memory or {}).get("last_update", {}).get("keys") and "pain_score" in memory["last_update"]["keys"]:
            score = next((f["value"] for f in memory.get("facts", []) if f.get("key") == "pain_score" and f.get("status") == "active"), None)
            if score is not None:
                turn.required += f"\nStart with a new fact: \"Pain {score}/10 after the blow is compatible with a possible concussion\"."
        reason = None
        correlation = str(request_id or uuid4())
        for attempt in (1, 2, 3):
            payload = {"model": self.model, "stream": False, "think": False, "keep_alive": "30m",
                       "options": {"temperature": 0, "num_predict": NUM_PREDICT, "num_ctx": NUM_CTX},
                       "messages": turn.messages(reason)}
            result = {}
            answer = ""
            category = None
            retryable = False
            input_bytes = sum(nbytes(m["content"]) for m in payload["messages"])
            try:
                if input_bytes > INPUT_BUDGET:
                    # Even the indispensable latest message + linked question exceed
                    # our conservative byte budget. Never silently truncate either.
                    raise OverflowError
                request = Request(self.base_url + "/api/chat", data=json.dumps(payload).encode(),
                                  headers={"Content-Type": "application/json"})
                with urlopen(request, timeout=90) as response:
                    result = json.loads(response.read(120_000))
                if not isinstance(result, dict):
                    result = {}
                    raise ValueError("invalid_envelope")
                answer = result["message"]["content"].strip()
                # Formatting is presentation noise, not a reason to discard a
                # clinically grounded model answer after an expensive retry.
                answer = answer.replace("**", "")
                answer = re.sub(r"(?m)^\s{0,3}#{1,4}\s+", "", answer)
                answer = re.sub(r"(?m)^\s*(?:[-•]|\d+[.)])\s+", "", answer)
                answer = re.sub(r"^(?:Следующий шаг|Ответ|Next step|Answer)\s*:\s*", "", answer, flags=re.I)
                # Source names belong in citations, not in conversational prose.
                answer = re.sub(r"(?:the )?source URL provided:\s*https?://[^\s)]+",
                                "the linked source.", answer, flags=re.I)
                answer = re.sub(r"https?://[^\s)]+", "the linked source", answer)
                answer = re.sub(
                    r"\b(?:Canadian Space Agency|Inspiration4|NASA|OCHMO|OSDR|CSA)\b",
                    "the source", answer, flags=re.I,
                )
                if (turn.move == "food_update" and "Signs of dehydration: absent" in turn.user_facts
                        and not re.search(r"обезвож|dehydrat", answer, re.I)):
                    answer = "You reported no signs of dehydration. " + answer
                category = ("generation_truncated" if result.get("done_reason") == "length" else validate(answer, turn))
                if not category and turn.topic == "bleeding" and _spurting(episode) and not re.search(
                    r"приж|давлен|давите|press|pressure|compress", answer.casefold()
                ):
                    category = "missing_bleeding_action"
                if not category and turn.topic == "fever_headache":
                    for number in re.findall(r"\b(\d{2}(?:[.,]\d+)?)\s*°", answer):
                        if not any(number.replace(",", ".") in piece.replace(",", ".") for piece in
                                   [turn.latest, *turn.evidence]):
                            category = "unsupported_temperature"
                if not category:
                    for number in re.findall(r"\b(10|[0-9])\s*/\s*10\b", answer):
                        supplied = bool(re.search(rf"\b{number}\s*(?:из\s*10|/\s*10|балл\w*|out of 10|points?)", " ".join(episode), re.I))
                        if not supplied and not any(str(f.get("value")) == number and f.get("key") == "pain_score"
                                                     and f.get("status") == "active" and f.get("user_message_id")
                                                     for f in (memory or {}).get("facts", [])):
                            category = "unsupported_score"
                retryable = bool(category)
            except HTTPError as exc:
                # Inspect the API error locally; never propagate its body to diagnostics.
                detail = exc.read(2000).decode(errors="replace").casefold()
                category = ("context_limit" if "context" in detail and re.search(r"length|limit|exceed|too long", detail)
                            else "model_unavailable" if exc.code == 404 else "transport_http_error")
            except TimeoutError:
                category = "timeout"
            except OverflowError:
                category = "context_limit"
            except OSError as exc:
                category = "timeout" if isinstance(getattr(exc, "reason", None), TimeoutError) else "connection_error"
            except (ValueError, TypeError, AttributeError, KeyError):
                category = "parsing_failure"
                retryable = True
            will_retry = retryable and (attempt == 1 or (attempt == 2 and category in {"repeated_answer", "unsupported_timing"}))
            counts = {name: result[name] if type(result.get(name)) is int else "unavailable"
                      for name in ("prompt_eval_count", "eval_count")}
            finish = result.get("done_reason")
            logger.info("chat_generation_attempt", extra={
                "request_id": correlation, "attempt": attempt, "outcome": "rejected" if category else "accepted",
                "category": category or "ok", "input_utf8_bytes": input_bytes,
                **counts, "done_reason": finish if finish in ("stop", "length", "load", "unload") else "unavailable",
                "retry_reason": reason or "none", "will_retry": will_retry,
            })
            if not category:
                from app.chat_retrieval import case_source_links
                return {"answer": answer, "source_refs": [*turn.source_refs, *case_source_links(turn.source_refs)]}
            reason = ("repeated_answer_final" if category == "repeated_answer" and attempt == 2 else
                      "unsupported_timing_final" if category == "unsupported_timing" and attempt == 2 else category)
            if not will_retry:
                self._error.set(category)
                return None
        return None

    def extract(self, episode: list[str]) -> dict[str, Any] | None:
        if not self.enabled or not is_loopback_ollama_url(self.base_url):
            return None
        payload = {
            "model": self.model, "stream": False, "format": SCHEMA,
            "options": {"temperature": 0, "num_predict": 220},
            "messages": [
                {"role": "system", "content": (
                    "Extract only explicitly stated facts from English or Russian dialogue. "
                    "Do not diagnose or advise. Respect denials and corrections in the latest message. "
                    "If a short answer such as '4 out of 10' refers to a previous complaint, retain that topic. "
                    "Return only JSON matching the schema. An unmentioned symptom is unknown, not absent."
                )},
                {"role": "user", "content": json.dumps({"dialogue": episode}, ensure_ascii=False)},
            ],
        }
        try:
            request = Request(self.base_url + "/api/chat", data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                              headers={"Content-Type": "application/json"})
            with urlopen(request, timeout=35) as response:
                result = json.loads(response.read(100_000))
            facts = json.loads(result["message"]["content"])
            if (not isinstance(facts, dict) or facts.get("topic") not in {"food", "head", "fever_headache", "oxygen", "other"}
                    or any(key not in facts for key in SCHEMA["required"])):
                return None
            return facts
        except (OSError, ValueError, KeyError, TypeError):
            return None


def _known_facts(episode: list[str]) -> dict[str, Any]:
    joined = normalize_english(" ".join(episode))
    latest = normalize_english(episode[-1])
    codes = set(symptom_codes(joined))
    facts = {key: key in codes for key in ("head_impact", "abdominal_pain", "headache", "dizziness", "nausea", "vomiting", "diarrhea", "fever")}
    facts["spoiled_food"] = bool(re.search(r"\b(?:тухл\w*|испорч\w*|прокисш\w*|несвеж\w*)\b", joined))
    facts["bleeding_absent"] = bool(re.search(r"\b(?:кров\w*\s+нет|нет\s+кров\w*|без\s+кров\w*)\b", joined))
    facts["no_other_symptoms"] = bool(re.search(r"\b(?:больше|других|остальн\w*)\s+(?:ничего|симптом\w*|признак\w*)?.{0,25}\bнет\b|\bничего\s+(?:из\s+перечисленн\w*\s+)?нет\b", latest))
    severity = re.search(r"\b(10|[0-9])\s*(?:из\s*10|/\s*10|балл\w*|out of 10|points?)\b", latest)
    facts["severity"] = int(severity.group(1)) if severity else None
    delay = re.search(r"\b(?:спустя|через|after|in)\s+(\d+(?:[.,]\d+)?|один|одного|два|две|тр[иеё]х?|четыре|пять|шесть|семь|восемь|девять|десять|двенадцать|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+(?:час\w*|hours?)", joined)
    if not delay:
        delay = re.search(r"\b(\d+(?:[.,]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+hours?\s+(?:after|later)", joined)
    number_words = {"один": 1, "одного": 1, "два": 2, "две": 2, "три": 3, "трех": 3,
                    "четыре": 4, "пять": 5, "шесть": 6, "семь": 7, "восемь": 8,
                    "девять": 9, "десять": 10, "двенадцать": 12,
                    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}
    raw_delay = delay.group(1) if delay else None
    facts["delay_hours"] = (float(raw_delay.replace(",", ".")) if raw_delay and raw_delay[0].isdigit()
                            else number_words.get(raw_delay))
    return facts


def _spurting(episode: list[str]) -> bool:
    text = " ".join(episode).casefold()
    return bool(re.search(r"\b(?:фонтан\w*|стру[еёйю]\w*|хлещ\w*|spurting|gushing|squirting)\b", text))


def respond(messages: list[str], observations: list[Observation], analysis: dict[str, Any],
            model: LocalChatModel | None = None,
            conversation: list[dict[str, str]] | None = None, *, memory=None, request_id=None) -> tuple[str, list[str], str]:
    topic, episode = current_episode(messages)
    repeated = (len(messages) > 1 and messages[-1].strip().casefold() == messages[-2].strip().casefold())
    if model and hasattr(model, "generate") and episode:
        dialogue = conversation or []
        start = next((index for index in range(len(dialogue) - 1, -1, -1)
                      if dialogue[index].get("role") == "user" and dialogue[index].get("content") == episode[0]), 0)
        focused = dialogue[max(0, start - 2) if repeated else start:]
        if memory is not None or request_id is not None:
            generated = model.generate(episode, dialogue, observations, analysis, topic,
                                       memory=memory, request_id=request_id)
        else:
            generated = model.generate(episode, focused, observations, analysis, topic)
        if generated:
            answer = generated["answer"]
            return answer, generated.get("source_refs", []), f"local_model:{model.model}"
        # In normal product mode, never disguise a rejected/unavailable model
        # call as an AI answer assembled by deterministic medical templates.
        if getattr(model, "enabled", False):
            failure = getattr(model, "last_validation_error", None)
            return (
                ("No connection to the local model. Message saved, analysis not performed."
                 if failure == "connection_error" else
                 "Message saved. To respond, shorten the long message or split it into parts."
                 if failure == "context_limit" else
                 "The model repeated the previous answer. Message saved; new answer not provided."
                 if failure == "repeated_answer" else
                 "Message saved. The model did not complete the answer, analysis not performed."),
                [], f"local_model_error:{getattr(model, 'model', 'unknown')}",
            )
    model_facts = model.extract(episode) if model and episode else None
    # Model output can suggest a topic, but never supplies evidence or numbers.
    facts = _known_facts(episode) if episode else {}
    if topic is None and model_facts and model_facts["topic"] != "other":
        topic = model_facts["topic"]
    engine = "offline_rules"
    if topic == "bleeding" and _spurting(episode):
        card = cases()["bleeding"]
        latest = episode[-1].casefold()
        already = "You have already applied a bandage. " if re.search(r"\b(?:приложил\w*|прижал\w*|наложил\w*|applied|pressed|bandaged)\b", latest) else ""
        help_coming = "Help is on the way; keep applying direct pressure until it arrives. " if re.search(r"помощ\w*\s+в\s+пути|help is (?:on the way|coming)", latest) else ""
        return (f"This is a severe external bleeding from the hand requiring immediate assistance. {already}{help_coming}"
                " Continuously and firmly press the bleeding site through the bandage; do not remove the first layer. "
                "Tell the arriving responders that the blood is spurting. "
                "If the bleeding does not stop, a trained person may apply an appropriate tourniquet on the arm above the wound. "
                "Lack of numbness and apparent shallow wound do not reduce urgency.", [], "offline_rules")
    if topic == "food" and facts.get("abdominal_pain") and facts.get("spoiled_food"):
        card = cases()["food"]
        time = f" through {facts['delay_hours']:g} hr" if facts.get("delay_hours") is not None else ""
        exposure = " after a meal you considered spoiled" if facts.get("spoiled_food") else ""
        evidence = f"You described spasms or pain in the abdomen{time}{exposure}."
        additions = [name for key, name in (("diarrhea", "diarrhea"), ("vomiting", "vomiting"), ("nausea", "nausea")) if facts.get(key)]
        if additions:
            evidence += f" Also you reported: {', '.join(additions)}."
        clarification = ("You already mentioned that there are no other listed symptoms." if facts.get("no_other_symptoms") else "")
        missing = [name for key, name in (("vomiting", "vomiting"), ("diarrhea", "diarrhea")) if not facts.get(key)]
        question = ("If the condition changes, write about new symptoms and the time they appeared." if facts.get("no_other_symptoms")
                    else f"Clarify whether there is {', '.join(missing + ['fever'])}, whether the pain is severe or localized, and whether you can drink.")
        if repeated:
            timing = f" approximately through {facts['delay_hours']:g} hr" if facts.get("delay_hours") is not None else ""
            return (f"I already considered this complaint: pain in the abdomen{timing} after suspicious food."
                    f"The preliminary version remains: {card['candidate']}.\n"
                    f"To clarify the cause and urgency, new information is needed. {question}\n"
                    f"For now: {card['actions']} {card['red_flags']}", card["source_urls"], engine)
        answer = (f"Preliminary version: {card['candidate']}.\n"
                  f"Why: {evidence} {card['support']}\n"
                  f"What to do now: {card['actions']}\n"
                  f"When help is needed: {card['red_flags']}\n"
                  f"Clarification: {clarification}{question}")
        return answer, card["source_urls"], engine
    if topic == "food" and facts.get("abdominal_pain"):
        return ("You described abdominal pain or cramps. The cause based on this phrase cannot be determined yet.\n"
                "What to do now: mark the location, intensity, and time of onset of the pain; if possible, drink water in small amounts.\n"
                "Clarification: where exactly is the pain, how severe is it on a scale of 0–10, is there vomiting, diarrhea, or fever, was there any unusual food?\n"
                "When to seek help: if the pain is severe or worsening, if there is blood in the stool, repeated vomiting, or if you are unable to drink, inform the onboard medical officer.",
                ["https://www.nhs.uk/symptoms/stomach-ache/"], engine)
    if topic == "head" and facts.get("head_impact"):
        card = cases()["head"]
        details = []
        if facts.get("headache"):
            details.append("headache")
        if facts.get("dizziness"):
            details.append("dizziness")
        if facts.get("vomiting"):
            details.append("vomiting")
        elif facts.get("nausea"):
            details.append("nausea")
        if facts.get("severity") is not None:
            details.append(f"pain intensity {facts['severity']}/10")
        if facts.get("bleeding_absent"):
            details.append("no external bleeding")
        evidence = f"You reported a head injury and indicated {', '.join(details)}." if details else "You reported a head injury."
        candidate = card["candidate"] if facts.get("headache") or facts.get("dizziness") else "head trauma; presence of concussion is unclear"
        question = ("You mentioned that there are no other listed symptoms; if they appear, please write immediately and inform the responsible person." if facts.get("no_other_symptoms")
                    else "Clarify: was there loss of consciousness, vomiting, confusion, or change in vision? Is the pain increasing?")
        support = card["support"] if facts.get("headache") and facts.get("dizziness") else (
            "Symptoms after the blow may correspond to a concussion; absence of blood outside does not exclude it."
            "It cannot be confirmed as a concussion via correspondence.")
        followup = len(episode) > 1 and explicit_topic(episode[-1]) is None
        if followup:
            changed = (f"Pain {facts['severity']}/10" if facts.get("severity") is not None else "New clarification")
            if facts.get("no_other_symptoms"):
                changed += "; no other listed symptoms, according to your words"
            answer = (f"Clarification taken into account: {changed}.\n"
                      f"Preliminary version: {candidate}. {evidence} {support}\n"
                      f"Next step: {card['actions']}\n"
                      f"If worsening: {card['red_flags']}")
        else:
            answer = (f"Preliminary version: {candidate}.\n"
                      f"Why: {evidence} {support}\n"
                      f"What to do now: {card['actions']}\n"
                      f"When help is needed: {card['red_flags']}\n"
                      f"Clarification: {question}")
        return answer, card["source_urls"], engine
    answer, sources = reply_to_message(episode or messages, observations, analysis)
    return answer, sources, engine
