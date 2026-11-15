"""Assemble eight verified HTTP range parts of Qwen3-8B shard 2."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve(strict=True)
    manifest = json.loads(Path(__file__).with_name("qwen3-8b-weights-manifest.json").read_text(encoding="utf-8"))
    item = manifest["files"][1]
    target = directory / item["name"]
    part_size = item["bytes"] // 8
    assert part_size * 8 == item["bytes"]
    parts = [directory / f"{item['name']}.part{i:02d}" for i in range(8)]
    for path in parts:
        if path.resolve().parent != directory or not path.is_file() or path.stat().st_size != part_size:
            raise SystemExit(f"Missing or incomplete range part: {path}")
    assembled = directory / f"{item['name']}.assembled"
    digest = hashlib.sha256()
    with assembled.open("wb") as output:
        for path in parts:
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(16 * 1024 * 1024), b""):
                    output.write(chunk)
                    digest.update(chunk)
    if assembled.stat().st_size != item["bytes"] or digest.hexdigest() != item["sha256"]:
        assembled.unlink()
        raise SystemExit("Assembled shard has wrong size or SHA256")
    os.replace(assembled, target)
    for path in parts:
        path.unlink()
    print(f"Verified and assembled {target}")


if __name__ == "__main__":
    main()
