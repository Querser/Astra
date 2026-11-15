"""Evaluate the unmodified local Ollama model on fictional held-out ASTRA cases.

This is a research benchmark, not a clinical validation or the production chat path.
Only local loopback inference and repository knowledge cards are used.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "model-led"
SYSTEM_PROMPT = (
    "\u0422\u044b ASTRA, \u0438\u0441\u0441\u043b\u0435\u0434\u043e\u0432\u0430\u0442\u0435\u043b\u044c\u0441\u043a\u0438\u0439 \u0430\u0432\u0442\u043e\u043d\u043e\u043c\u043d\u044b\u0439 \u0430\u0441\u0441\u0438\u0441\u0442\u0435\u043d\u0442 \u0434\u043b\u044f \u0432\u044b\u043c\u044b\u0448\u043b\u0435\u043d\u043d\u043e\u0433\u043e \u044d\u043a\u0438\u043f\u0430\u0436\u0430. "
    "\u041f\u0440\u043e\u0447\u0442\u0438 \u0432\u0441\u0435 \u0440\u0435\u043f\u043b\u0438\u043a\u0438 \u043a\u0430\u043a \u043e\u0434\u0438\u043d \u044d\u043f\u0438\u0437\u043e\u0434, \u0443\u0447\u0438\u0442\u044b\u0432\u0430\u0439 \u043d\u043e\u0432\u044b\u0435 \u0444\u0430\u043a\u0442\u044b \u0438 \u043e\u0442\u0440\u0438\u0446\u0430\u043d\u0438\u044f. "
    "\u0420\u0435\u0448\u0435\u043d\u0438\u0435 \u043e \u0434\u0438\u0430\u0433\u043d\u043e\u0441\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0445 \u0432\u0435\u0440\u0441\u0438\u044f\u0445 \u0438 \u0432\u043e\u043f\u0440\u043e\u0441\u0430\u0445 \u043f\u0440\u0438\u043c\u0438 \u0441\u0430\u043c \u043d\u0430 \u043e\u0441\u043d\u043e\u0432\u0430\u043d\u0438\u0438 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0435\u0440\u0435\u0434\u0430\u043d\u043d\u044b\u0445 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0445 \u043a\u0430\u0440\u0442\u043e\u0447\u0435\u043a. "
    "\u0415\u0441\u043b\u0438 \u0444\u0430\u043a\u0442\u044b \u043d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442 \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443, \u043d\u0435 \u043d\u0430\u0437\u044b\u0432\u0430\u0439 \u0435\u0451. \u041f\u0440\u0438 \u043d\u043e\u0440\u043c\u0430\u043b\u044c\u043d\u044b\u0445 \u0434\u0430\u043d\u043d\u044b\u0445 candidate_ids=[]. "
    "\u041a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u0443\u044e \u0431\u043e\u043b\u0435\u0437\u043d\u044c \u043d\u0430\u0437\u044b\u0432\u0430\u0439 \u0442\u043e\u043b\u044c\u043a\u043e \u043f\u0440\u0435\u0434\u0432\u0430\u0440\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0439 \u0432\u0435\u0440\u0441\u0438\u0435\u0439, \u043e\u0431\u044a\u044f\u0441\u043d\u0438 \u0444\u0430\u043a\u0442\u044b \u0437\u0430 \u0438 \u043d\u0435\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d\u043d\u043e\u0441\u0442\u044c. "
    "\u041d\u0435 \u043f\u0440\u0438\u0434\u0443\u043c\u044b\u0432\u0430\u0439 \u0438\u0437\u043c\u0435\u0440\u0435\u043d\u0438\u044f, \u0434\u0438\u0430\u0433\u043d\u043e\u0437\u044b, \u0434\u043e\u0437\u044b, \u043b\u0435\u043a\u0430\u0440\u0441\u0442\u0432\u0430, \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u0438. "
    "\u041f\u0440\u0438 \u043e\u0447\u0435\u0432\u0438\u0434\u043d\u043e\u0439 \u0443\u0433\u0440\u043e\u0437\u0435 \u0441\u043d\u0430\u0447\u0430\u043b\u0430 \u043d\u0430\u0437\u043e\u0432\u0438 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u043f\u0440\u0430\u043a\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u0448\u0430\u0433. "
    "\u041d\u0435 \u043f\u043e\u0432\u0442\u043e\u0440\u044f\u0439 \u0443\u0436\u0435 \u0441\u043e\u043e\u0431\u0449\u0451\u043d\u043d\u043e\u0435 \u043a\u0430\u043a \u0432\u043e\u043f\u0440\u043e\u0441 \u0438 \u043d\u0435 \u0434\u0443\u0431\u043b\u0438\u0440\u0443\u0439 \u043f\u0440\u0435\u0436\u043d\u0438\u0439 \u043e\u0442\u0432\u0435\u0442. "
    "\u0412\u0435\u0440\u043d\u0438 \u0442\u043e\u043b\u044c\u043a\u043e JSON: candidate_ids (\u043c\u0430\u0441\u0441\u0438\u0432 ID \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0445 \u043a\u0430\u0440\u0442\u043e\u0447\u0435\u043a), "
    "urgency (routine|prompt_review|emergency), answer_ru (3–6 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0439), "
    "used_knowledge_ids (\u043c\u0430\u0441\u0441\u0438\u0432 ID)."
)


def tokens(text: str) -> set[str]:
    return {word[:5] for word in re.findall(r"[\u0430-\u044f\u0451a-z0-9]{5,}", text.casefold())}


def retrieve(message: str, cards: list[dict], count: int = 6) -> list[dict]:
    query = tokens(message)
    ranked = []
    for card in cards:
        content = " ".join(str(card.get(key, "")) for key in
                           ("name_ru", "evidence_for", "evidence_against", "ask_if_unknown", "do_not_infer"))
        score = len(query & tokens(content))
        ranked.append((score, card["id"], card))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:count] if item[0] > 0]


def ask_model(url: str, model: str, messages: list[str], cards: list[dict]) -> tuple[dict | None, str, float]:
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 260, "num_ctx": 4096},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "episode_messages": messages,
                "local_cards": cards,
            }, ensure_ascii=False)},
        ],
    }
    started = time.monotonic()
    request = Request(url.rstrip("/") + "/api/chat",
                      data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json"})
    with urlopen(request, timeout=180) as response:
        result = json.load(response)
    raw = result.get("message", {}).get("content", "")
    elapsed = round(time.monotonic() - started, 2)
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        parsed = None
    return parsed, raw, elapsed


def evaluate(case: dict, parsed: dict | None, retrieved: list[str]) -> dict:
    retrieval_hit = set(case["expected_ids"]).issubset(set(retrieved))
    if not isinstance(parsed, dict):
        return {"parse_ok": False, "ids_exact": False, "urgency_ok": False,
                "mentions_ok": False, "exclusions_ok": False, "grounding_ok": False,
                "retrieval_hit": retrieval_hit}
    ids = parsed.get("candidate_ids")
    used = parsed.get("used_knowledge_ids")
    answer = parsed.get("answer_ru")
    if not isinstance(ids, list) or not isinstance(used, list) or not isinstance(answer, str):
        return {"parse_ok": False, "ids_exact": False, "urgency_ok": False,
                "mentions_ok": False, "exclusions_ok": False, "grounding_ok": False,
                "retrieval_hit": retrieval_hit}
    lowered = answer.casefold().replace("\u0451", "\u0435")
    return {
        "parse_ok": True,
        "ids_exact": set(ids) == set(case["expected_ids"]),
        "urgency_ok": parsed.get("urgency") == case["urgency"],
        "mentions_ok": all(term.casefold().replace("\u0451", "\u0435") in lowered for term in case["must_mention"]),
        "exclusions_ok": all(term.casefold().replace("\u0451", "\u0435") not in lowered for term in case["must_not"]),
        "grounding_ok": set(ids + used).issubset(set(retrieved)),
        "retrieval_hit": retrieval_hit,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Run first N cases; 0 means all")
    parser.add_argument("--output", type=Path, default=PACK / "baseline-results.json")
    args = parser.parse_args()
    url = os.getenv("ASTRA_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    if not re.fullmatch(r"http://(?:127\.0\.0\.1|localhost):\d+", url.rstrip("/")):
        raise SystemExit("Only a local loopback Ollama server is allowed")
    model = os.getenv("ASTRA_OLLAMA_MODEL", "qwen3:8b")
    cards_data = json.loads((PACK / "knowledge_cards.json").read_text(encoding="utf-8"))
    cases_data = json.loads((PACK / "eval_cases.json").read_text(encoding="utf-8"))
    cases = cases_data["cases"][:args.limit or None]
    rows = []
    for index, case in enumerate(cases, 1):
        selected = retrieve(" ".join(case["messages"]), cards_data["cards"])
        retrieved = [card["id"] for card in selected]
        try:
            parsed, raw, seconds = ask_model(url, model, case["messages"], selected)
            error = None
        except Exception as exc:  # record failure without converting it to a pass
            parsed, raw, seconds, error = None, "", 0, f"{type(exc).__name__}: {exc}"
        checks = evaluate(case, parsed, retrieved)
        rows.append({"case_id": case["id"], "retrieved_ids": retrieved,
                     "expected_ids": case["expected_ids"], "expected_urgency": case["urgency"],
                     "response": parsed, "raw_response": raw, "seconds": seconds,
                     "error": error, "checks": checks})
        print(f"{index}/{len(cases)} {case['id']}: "
              f"ids={checks['ids_exact']} urgency={checks['urgency_ok']} "
              f"grounded={checks['grounding_ok']} {seconds}s", flush=True)
    metrics = {key: {"passed": sum(bool(row["checks"][key]) for row in rows), "total": len(rows)}
               for key in ("parse_ok", "ids_exact", "urgency_ok", "mentions_ok", "exclusions_ok", "grounding_ok", "retrieval_hit")}
    emergencies = [row for row in rows if row["expected_urgency"] == "emergency"]
    metrics["emergency_recall"] = {
        "passed": sum(row["response"] is not None and row["response"].get("urgency") == "emergency"
                      for row in emergencies), "total": len(emergencies)}
    report = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "model": model,
              "knowledge_version": cards_data["version"], "cases_version": cases_data["version"],
              "purpose": "pilot only; provisional labels, not clinical accuracy",
              "metrics": metrics, "cases": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {args.output}")
    print(json.dumps(metrics, ensure_ascii=False))


if __name__ == "__main__":
    main()
