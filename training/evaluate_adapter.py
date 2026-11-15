"""Compare a local QLoRA adapter with the frozen 24-case baseline protocol."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from evaluate_model_baseline import SYSTEM_PROMPT, evaluate, retrieve  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--adapter", type=Path)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--cases", type=Path, default=ROOT / "docs/model-led/eval_cases.json")
    parser.add_argument("--compact-v2", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU required")
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                               bnb_4bit_use_double_quant=True, bnb_4bit_compute_dtype=dtype)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    base = AutoModelForCausalLM.from_pretrained(
        args.model, quantization_config=quant, dtype=dtype,
        device_map={"": 0}, attn_implementation="sdpa", low_cpu_mem_usage=True)
    model = PeftModel.from_pretrained(base, args.adapter) if args.adapter else base
    model.eval()
    pack = ROOT / "docs/model-led"
    cards = json.loads((pack / "knowledge_cards.json").read_text(encoding="utf-8"))["cards"]
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"][:args.limit or None]
    if args.compact_v2:
        from build_casebook_v2 import SYSTEM_PROMPT_V2, project_cards
    rows = []
    for index, case in enumerate(cases, 1):
        selected = retrieve(" ".join(case["messages"]), cards, count=4 if args.compact_v2 else 6)
        context_cards = project_cards(selected) if args.compact_v2 else selected
        context = {"episode_messages": case["messages"], "local_cards": context_cards}
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_V2 if args.compact_v2 else SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
        ]
        encoded = tokenizer.apply_chat_template(messages, tokenize=True,
                                                add_generation_prompt=True,
                                                enable_thinking=False,
                                                return_tensors="pt")
        input_ids = encoded["input_ids"].to("cuda")
        started = time.monotonic()
        try:
            with torch.inference_mode():
                generated = model.generate(input_ids=input_ids, max_new_tokens=260,
                                           do_sample=False, pad_token_id=tokenizer.eos_token_id)
            raw = tokenizer.decode(generated[0, input_ids.shape[1]:], skip_special_tokens=True)
            parsed = json.loads(raw)
            error = None
        except Exception as exc:
            raw, parsed, error = "", None, f"{type(exc).__name__}: {exc}"
        checks = evaluate(case, parsed, [item["id"] for item in selected])
        rows.append({"case_id": case["id"], "response": parsed, "raw": raw, "error": error,
                     "seconds": round(time.monotonic() - started, 2), "checks": checks})
        print(f"{index}/{len(cases)} {case['id']}: ids={checks['ids_exact']} "
              f"urgency={checks['urgency_ok']}", flush=True)
    metrics = {key: {"passed": sum(bool(row["checks"][key]) for row in rows), "total": len(rows)}
               for key in ("parse_ok", "ids_exact", "urgency_ok", "mentions_ok",
                           "exclusions_ok", "grounding_ok")}
    by_case = {case["id"]: case for case in cases}
    emergencies = [row for row in rows if by_case[row["case_id"]]["urgency"] == "emergency"]
    metrics["emergency_recall"] = {"passed": sum(
        row["response"] is not None and row["response"].get("urgency") == "emergency"
        for row in emergencies), "total": len(emergencies)}
    output = args.output or ((args.adapter / "eval_24_cases.json") if args.adapter else \
        (ROOT / "training/artifacts/qwen3-8b-base-eval.json")
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"status": "pilot_comparison_not_clinical_validation",
                                  "variant": "pilot_adapter" if args.adapter else "quantized_base",
                                  "context_mode": "compact_v2" if args.compact_v2 else "pilot_v1",
                                  "cases_file": str(args.cases),
                                  "metrics": metrics, "cases": rows}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(metrics, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
