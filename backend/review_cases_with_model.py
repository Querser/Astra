"""Blind consistency review using a second, local model.

The model sees the vignette and local card(s), never the author's expected label.
Its agreement is a machine check, not independent medical validation.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "docs" / "model-led"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--one-per-pattern", action="store_true")
    parser.add_argument("--output", type=Path, default=PACK / "review_cases_240_model_check.json")
    args = parser.parse_args()
    url = os.getenv("ASTRA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    if url not in {"http://127.0.0.1:11434", "http://localhost:11434"}:
        raise SystemExit("Only loopback Ollama is allowed")
    model = os.getenv("ASTRA_REVIEW_MODEL", "qwen2.5vl:3b")
    by_id = {card["id"]: card for card in json.loads((PACK / "knowledge_cards.json").read_text(encoding="utf-8"))["cards"]}
    cases = json.loads((PACK / "review_cases_240.json").read_text(encoding="utf-8"))["cases"]
    if args.one_per_pattern:
        seen = set()
        selected = []
        for case in cases:
            key = (case["family"], case["pattern"])
            if key not in seen:
                selected.append(case)
                seen.add(key)
        cases = selected
    cases = cases[:args.limit or None]
    completed = {}
    if args.output.exists():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        if previous.get("model") == model:
            completed = {row["id"]: row for row in previous.get("reviews", [])}
    reviews = []
    for index, case in enumerate(cases, 1):
        if case["id"] in completed:
            reviews.append(completed[case["id"]])
            continue
        primary = f"ASTRA.K.{case['family']}"
        chosen = [by_id[primary]]
        if case["family"] == "BONE":
            chosen.append(by_id["ASTRA.K.MUSCLE"])
        # Exclude the author's expected IDs and label note from the model input.
        payload = {
            "model": model, "stream": False, "think": False, "format": "json",
            "options": {"temperature": 0, "num_predict": 180, "num_ctx": 4096},
            "messages": [
                {"role": "system", "content": (
                    "\u0422\u044b \u043d\u0435\u0437\u0430\u0432\u0438\u0441\u0438\u043c\u044b\u0439 \u043f\u0440\u043e\u0432\u0435\u0440\u044f\u044e\u0449\u0438\u0439 \u0432\u044b\u043c\u044b\u0448\u043b\u0435\u043d\u043d\u043e\u0433\u043e \u0443\u0447\u0435\u0431\u043d\u043e\u0433\u043e \u0441\u043b\u0443\u0447\u0430\u044f. "
                    "\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0438, \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442 \u043b\u0438 \u0444\u0430\u043a\u0442\u044b \u0438\u043c\u0435\u043d\u043d\u043e \u043a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u0430 \u0438\u043b\u0438 \u0440\u0438\u0441\u043a \u0438\u0437 \u043f\u0435\u0440\u0435\u0434\u0430\u043d\u043d\u044b\u0445 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0445 \u043a\u0430\u0440\u0442\u043e\u0447\u0435\u043a. "
                    "\u0423\u043f\u043e\u043c\u0438\u043d\u0430\u043d\u0438\u0435 \u0431\u043e\u043b\u0435\u0437\u043d\u0438, \u043e\u0442\u0440\u0438\u0446\u0430\u043d\u0438\u0435 \u0441\u0438\u043c\u043f\u0442\u043e\u043c\u0430, \u0435\u0434\u0438\u043d\u0438\u0447\u043d\u044b\u0439 \u0432\u044b\u0431\u0440\u043e\u0441 \u0438\u043b\u0438 \u043d\u0435\u0441\u043e\u043f\u043e\u0441\u0442\u0430\u0432\u0438\u043c\u044b\u0439 \u0442\u0435\u0441\u0442 \u0441\u0430\u043c\u0438 \u043f\u043e \u0441\u0435\u0431\u0435 \u043d\u0435 \u043f\u043e\u0434\u0434\u0435\u0440\u0436\u0438\u0432\u0430\u044e\u0442 \u043a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u0430. "
                    "\u041d\u0435 \u0443\u0433\u0430\u0434\u044b\u0432\u0430\u0439 \u0437\u0430\u0431\u043e\u043b\u0435\u0432\u0430\u043d\u0438\u0435 \u0432\u043d\u0435 \u043a\u0430\u0440\u0442\u043e\u0447\u0435\u043a. \u0421\u0440\u043e\u0447\u043d\u043e\u0441\u0442\u044c: emergency \u043f\u0440\u0438 \u044f\u0432\u043d\u043e\u0439 \u043d\u0435\u043f\u043e\u0441\u0440\u0435\u0434\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0439 \u0443\u0433\u0440\u043e\u0437\u0435, "
                    "prompt_review \u043f\u0440\u0438 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e\u0441\u0442\u0438 \u043e\u043f\u0435\u0440\u0430\u0442\u0438\u0432\u043d\u043e\u0439 \u043e\u0446\u0435\u043d\u043a\u0438, \u0438\u043d\u0430\u0447\u0435 routine. "
                    "\u0412\u0435\u0440\u043d\u0438 JSON: candidate_ids (\u043c\u0430\u0441\u0441\u0438\u0432), urgency (routine|prompt_review|emergency), reason_ru (1 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0435).")},
                {"role": "user", "content": json.dumps({
                    "messages": case["messages"],
                    "cards": chosen,
                }, ensure_ascii=False)},
            ],
        }
        request = Request(url + "/api/chat", json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          {"Content-Type": "application/json"})
        started = time.monotonic()
        try:
            with urlopen(request, timeout=180) as response:
                result = json.load(response)
            raw = result.get("message", {}).get("content", "")
            review = json.loads(raw)
            error = None
        except Exception as exc:
            review, raw, error = None, "", f"{type(exc).__name__}: {exc}"
        ids = review.get("candidate_ids") if isinstance(review, dict) else None
        urgency = review.get("urgency") if isinstance(review, dict) else None
        row = {"id": case["id"], "review": review, "error": error,
               "seconds": round(time.monotonic() - started, 2),
               "candidate_agreement": isinstance(ids, list) and set(ids) == set(case["expected_candidate_ids"]),
               "urgency_agreement": urgency == case["expected_urgency"]}
        reviews.append(row)
        print(f"{index}/{len(cases)} {case['id']} ids={row['candidate_agreement']} "
              f"urgency={row['urgency_agreement']} {row['seconds']}s", flush=True)
        if index % 10 == 0 or index == len(cases):
            report = {"run_at_utc": datetime.now(timezone.utc).isoformat(), "model": model,
                      "status": "blind_machine_consistency_review_not_clinical_validation",
                      "reviews": reviews}
            args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Reviewed {len(reviews)}: ids={sum(row['candidate_agreement'] for row in reviews)}, "
          f"urgency={sum(row['urgency_agreement'] for row in reviews)}")


if __name__ == "__main__":
    main()
