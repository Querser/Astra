"""Small QLoRA feasibility pilot for the trainable Qwen3 checkpoint.

This script does not deploy its adapter or assert medical accuracy. The holdout
sets under docs/model-led are never read by this training loop.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-8B")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--corpus", type=Path, default=Path("training/data/pilot_sft.jsonl"))
    parser.add_argument("--learning-rate", type=float, default=8e-5)
    parser.add_argument("--save-every", type=int, default=0)
    parser.add_argument("--rank", type=int, default=8)
    parser.add_argument("--alpha", type=int, default=16)
    parser.add_argument("--target-modules", default="q_proj,v_proj")
    parser.add_argument("--urgency-weight", type=float, default=1.0)
    parser.add_argument("--output", type=Path, default=Path("training/artifacts/qwen3-8b-pilot"))
    args = parser.parse_args()

    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU required for this QLoRA pilot")
    target_modules = [item.strip() for item in args.target_modules.split(",") if item.strip()]
    if (args.max_steps < 1 or args.max_length < 128 or args.learning_rate <= 0 or
            args.save_every < 0 or args.rank < 1 or args.alpha < 1 or not target_modules or
            args.urgency_weight < 1):
        raise SystemExit("Invalid pilot size")
    corpus = args.corpus
    records = [json.loads(line) for line in corpus.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise SystemExit("Empty corpus")
    torch.manual_seed(42)
    compute_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    cache_dir = Path(os.getenv("ASTRA_TRAINING_CACHE", str(Path.home() / ".cache" / "astra-training")))
    print(f"Loading {args.model} in 4-bit on {torch.cuda.get_device_name(0)}", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, cache_dir=cache_dir)
    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        cache_dir=cache_dir,
        quantization_config=quantization,
        dtype=compute_dtype,
        device_map={"": 0},
        attn_implementation="sdpa",
        low_cpu_mem_usage=True,
    )
    model.config.use_cache = False
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)
    model = get_peft_model(model, LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05, bias="none",
        task_type="CAUSAL_LM", target_modules=target_modules,
    ))
    model.train()
    optimizer = torch.optim.AdamW((p for p in model.parameters() if p.requires_grad), lr=args.learning_rate)
    losses = []
    urgency_tokens_weighted = []
    for step in range(args.max_steps):
        messages = records[(step * 17) % len(records)]["messages"]
        prompt_ids = tokenizer.apply_chat_template(
            messages[:-1], tokenize=True, add_generation_prompt=True, enable_thinking=False)["input_ids"]
        full_ids = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=False, enable_thinking=False)["input_ids"]
        if full_ids[:len(prompt_ids)] != prompt_ids:
            raise RuntimeError("Prompt/completion token alignment failed")
        if len(full_ids) > args.max_length:
            raise RuntimeError(f"Example {step} is {len(full_ids)} tokens; max-length={args.max_length}")
        labels = [-100] * len(prompt_ids) + full_ids[len(prompt_ids):]
        if all(label == -100 for label in labels):
            raise RuntimeError("No assistant tokens to train")
        input_tensor = torch.tensor([full_ids], device="cuda", dtype=torch.long)
        label_tensor = torch.tensor([labels], device="cuda", dtype=torch.long)
        optimizer.zero_grad(set_to_none=True)
        if args.urgency_weight == 1:
            output = model(input_ids=input_tensor, labels=label_tensor)
            loss = output.loss
            weighted_count = 0
        else:
            import torch.nn.functional as functional
            output = model(input_ids=input_tensor)
            assistant = json.loads(messages[-1]["content"])
            fragment = tokenizer.encode(assistant["urgency"], add_special_tokens=False)
            start = next((index for index in range(len(prompt_ids), len(full_ids) - len(fragment) + 1)
                          if full_ids[index:index + len(fragment)] == fragment), None)
            if start is None:
                raise RuntimeError(f"Urgency token span not found at step {step + 1}")
            weights = torch.ones_like(label_tensor, dtype=torch.float32)
            weights[:, start:start + len(fragment)] = args.urgency_weight
            shifted_logits = output.logits[:, :-1, :].contiguous()
            shifted_labels = label_tensor[:, 1:].contiguous()
            shifted_weights = weights[:, 1:].contiguous()
            active = shifted_labels.ne(-100)
            token_loss = functional.cross_entropy(
                shifted_logits.view(-1, shifted_logits.size(-1)),
                shifted_labels.view(-1), reduction="none", ignore_index=-100).view_as(shifted_labels)
            loss = (token_loss * shifted_weights * active).sum() / (shifted_weights * active).sum()
            weighted_count = len(fragment)
        if not torch.isfinite(loss):
            raise RuntimeError(f"Non-finite loss at step {step + 1}")
        loss.backward()
        optimizer.step()
        losses.append(round(float(loss.detach().cpu()), 5))
        urgency_tokens_weighted.append(weighted_count)
        print(f"step={step + 1}/{args.max_steps} loss={losses[-1]} "
              f"peak_cuda_allocated_mib={torch.cuda.max_memory_allocated() // (1024 * 1024)}", flush=True)
        if args.save_every and (step + 1) % args.save_every == 0 and step + 1 != args.max_steps:
            checkpoint = args.output / f"checkpoint-{step + 1}"
            checkpoint.mkdir(parents=True, exist_ok=True)
            model.save_pretrained(checkpoint)
            tokenizer.save_pretrained(checkpoint)
            print(f"Saved intermediate adapter to {checkpoint}", flush=True)
    args.output.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    metadata = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "pilot_adapter_not_validated_not_deployed",
        "base_model": args.model,
        "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
        "corpus": str(corpus),
        "steps": args.max_steps,
        "max_length": args.max_length,
        "learning_rate": args.learning_rate,
        "rank": args.rank,
        "alpha": args.alpha,
        "target_modules": target_modules,
        "urgency_weight": args.urgency_weight,
        "urgency_tokens_weighted_per_step": urgency_tokens_weighted,
        "losses": losses,
        "gpu": torch.cuda.get_device_name(0),
        "peak_cuda_allocated_mib": torch.cuda.max_memory_allocated() // (1024 * 1024),
    }
    (args.output / "astra_training_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved pilot adapter to {args.output}", flush=True)


if __name__ == "__main__":
    main()
