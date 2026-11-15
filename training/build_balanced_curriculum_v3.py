"""Balance the v2 author-draft training records without reading holdouts."""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "training/data"
OUT = DATA / "multiturn_sft_v3_balanced.jsonl"


def main() -> None:
    cases = {item["id"]: item for item in json.loads(
        (DATA / "casebook_v2.json").read_text(encoding="utf-8"))["cases"]}
    rows = [json.loads(line) for line in (DATA / "multiturn_sft_v2.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 32 and all(cases[row["case_id"]]["split"] == "train" for row in rows)
    by_urgency: dict[str, list[dict]] = {key: [] for key in ("routine", "prompt_review", "emergency")}
    for row in rows:
        by_urgency[cases[row["case_id"]]["urgency"]].append(row)

    # 24 exposures per urgency. This is controlled oversampling, not 72 independent cases.
    balanced = []
    for urgency, group in by_urgency.items():
        for index in range(24):
            source = group[index % len(group)]
            copy = json.loads(json.dumps(source, ensure_ascii=False))
            copy["curriculum"] = {"urgency": urgency, "repeat": index // len(group)}
            balanced.append(copy)
    random.Random(20261109).shuffle(balanced)
    assert Counter(item["curriculum"]["urgency"] for item in balanced) == {
        "routine": 24, "prompt_review": 24, "emergency": 24}
    assert {item["case_id"] for item in balanced} == {item["case_id"] for item in rows}
    OUT.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in balanced) + "\n",
                   encoding="utf-8")
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    repeats = Counter(item["case_id"] for item in balanced)
    print(f"records={len(balanced)} unique={len(repeats)} sha256={digest}")
    print("repeat_range", min(repeats.values()), max(repeats.values()))


if __name__ == "__main__":
    main()
