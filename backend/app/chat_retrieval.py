"""Local section index. Rebuild/inspect with: python -m app.chat_retrieval"""

from dataclasses import asdict, dataclass
from functools import lru_cache
import json
from pathlib import Path
import re


REFERENCE_DIR = Path(__file__).resolve().parents[1] / "reference_docs"
GUIDANCE_TOPICS = {
    "D.POSSIBLE_HYPOXEMIA": "oxygen", "D.POSSIBLE_HYPERTENSION": "blood_pressure",
    "D.SLEEP_DEFICIENCY_PATTERN": "sleep", "D.POSSIBLE_SLEEP_APNEA": "sleep",
    "D.POSSIBLE_HEAD_INJURY": "head",
}


@dataclass(frozen=True)
class Excerpt:
    topic: str
    section: str
    source_ref: str
    text: str


@lru_cache(maxsize=1)
def build_index() -> tuple[Excerpt, ...]:
    """Rebuild deterministically from the product cards; no profile store or network."""
    excerpts = []
    cases = "ASTRA_CHAT_CASES.json"
    for topic, card in json.loads((REFERENCE_DIR / cases).read_text(encoding="utf-8"))["cases"].items():
        for section in ("candidate", "support", "actions", "red_flags", "temperature_reference", "minor_actions", "severe_differential"):
            if section in card:
                excerpts.append(Excerpt(topic, section, f"{cases}#/cases/{topic}/{section}", card[section]))
    guidance = "ASTRA_DEMO_GUIDANCE.json"
    for key, card in json.loads((REFERENCE_DIR / guidance).read_text(encoding="utf-8"))["by_candidate"].items():
        for i, action in enumerate(card["actions"]):
            excerpts.append(Excerpt(GUIDANCE_TOPICS.get(key, key), f"action_{i}",
                                    f"{guidance}#/by_candidate/{key}/actions/{i}/statement", action["statement"]))
    return tuple(excerpts)


def retrieve(topic: str, latest: str, *, continuation: bool = False, pressure_detail: bool = False) -> list[Excerpt]:
    """Rank sections by the current information need, then take a bounded slice."""
    latest = latest.casefold()
    if pressure_detail or re.search(r"давлени|тонометр|манжет|blood pressure|cuff", latest):
        if topic not in {"head", "bleeding"}:
            topic = "blood_pressure"
    if topic == "bleeding" and re.search(r"крови\s+почти\s+нет|кровь\s+почти\s+не|almost no blood|very little blood", latest):
        return [row for row in build_index() if row.topic == "bleeding" and row.section == "minor_actions"]
    if topic == "headache" and re.search(r"(?:9|10)\s*/\s*10|что со мной|опух\w*\s+ше|ше[яию]\s+опух|what is wrong with me|swollen neck|neck swelling", latest):
        return [row for row in build_index() if row.topic == "headache" and row.section in {"severe_differential", "red_flags"}]
    sections = {
        "blood_pressure": ["action_0"],
        "oxygen": ["action_0", "action_1"],
        "sleep": ["action_0", "action_1"],
        "head": ["candidate", "actions", "red_flags"],
        "bleeding": ["actions", "red_flags"],
        "fever_headache": ["actions", "red_flags", "temperature_reference"],
        "fever": ["support", "actions", "red_flags"],
    }.get(topic, ["actions", "red_flags"] if continuation else ["candidate", "support", "actions", "red_flags"])
    return sorted((row for row in build_index() if row.topic == topic and row.section in sections),
                  key=lambda row: sections.index(row.section))[:4]


def case_source_links(refs: list[str]) -> list[str]:
    """Expose original URLs for the case sections actually used in this turn."""
    cases = json.loads((REFERENCE_DIR / "ASTRA_CHAT_CASES.json").read_text(encoding="utf-8"))["cases"]
    links = []
    for ref in refs:
        match = re.fullmatch(r"ASTRA_CHAT_CASES\.json#/cases/([^/]+)/([^/]+)", ref)
        if not match or match[1] not in cases:
            continue
        card = cases[match[1]]
        urls = ([card.get("minor_source_url")] if match[2] == "minor_actions" else
                card.get("severe_source_urls", []) if match[2] == "severe_differential" else card.get("source_urls", []))
        for url in urls:
            if url and "source:" + url not in links:
                links.append("source:" + url)
    return links


@lru_cache(maxsize=1)
def space_science_cards() -> tuple[dict, ...]:
    """Return the small, locally packaged NASA/CSA reference set."""
    path = REFERENCE_DIR / "ASTRA_SPACE_SCIENCE.json"
    if not path.exists():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    cards = payload.get("cards", [])
    if not isinstance(cards, list):
        raise ValueError("Space-science cards must be a list")
    retrieved_at = payload.get("retrieved_at")
    return tuple({**card, "retrieved_at": card.get("retrieved_at") or retrieved_at} for card in cards)


def retrieve_space_science(topic: str, latest: str, *, limit: int = 2) -> list[Excerpt]:
    """Choose cards for the current information need without loading a whole PDF."""
    query = latest.casefold()
    words = {word for word in re.findall(r"[\w₂]+", query) if len(word) >= 3}
    inferred_topic = ("sleep" if re.search(r"\b(?:сплю|спал|спала|спать|высп\w*|бессон\w*|сон|сна|сне|sleep|slept|insomnia)\b", query)
                      else "radiation" if re.search(r"радиац|излучен|облуч|доз|radiat|dose", query) else None)
    scored = []
    for card in space_science_cards():
        terms = [str(item).casefold() for item in card.get("keywords", []) if len(str(item)) >= 3]
        topic_name = str(card.get("topic", "")).casefold()
        if topic_name == "environment" and topic != "environment":
            if not re.search(r"co₂|co2|ppco2|кабин|атмосфер|воздух|отсек|сред[аыеу]|обитаем|скафандр|телеметр|стандарт|cabin|atmosphere|air|environment|spacesuit|telemetry|habitat|standard", latest.casefold()):
                continue
        title = str(card.get("title_ru", "")).casefold()
        score = sum(2 for term in terms if term in query)
        score += sum(1 for term in terms for word in words if len(term) >= 5 and word[:4] == term[:4])
        if topic_name == topic and topic not in {"general", "other"}:
            score += 2
        if topic_name == inferred_topic:
            score += 3
        stable_id = str(card.get("id", ""))
        if stable_id == "HRP.RISK.RADIATION_CANCER" and re.search(r"влияет|вред|здоров|риск|последств|affect|harm|health|risk|consequence", query):
            score += 6
        if stable_id == "CSA.RADIATION.CANS" and not re.search(r"cans|нейтрон|адаптер|будущ|разработ|neutron|adapter|future|develop", query):
            score -= 3
        if score <= 0 and not any(word in title for word in words):
            continue
        detail = {
            "title": card.get("title_ru"),
            "supported": card.get("supported_interpretation"),
            "missing": card.get("missing_inputs"),
            "actions": card.get("practical_actions"),
            "limits": card.get("limitations"),
        }
        if stable_id:
            scored.append((score, stable_id, Excerpt(
                topic_name, stable_id, f"ASTRA_SPACE_SCIENCE.json#{stable_id}",
                json.dumps(detail, ensure_ascii=False, separators=(",", ":")),
            )))
    scored.sort(key=lambda row: (-row[0], row[1]))
    return [row[2] for row in scored[:limit]]


if __name__ == "__main__":
    print(json.dumps([asdict(row) for row in build_index()], ensure_ascii=False, indent=2))
