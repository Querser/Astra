"""Verify downloaded Qwen3-8B shards against the official manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    manifest = json.loads((Path(__file__).with_name("qwen3-8b-weights-manifest.json")).read_text(encoding="utf-8"))
    for item in manifest["files"]:
        path = args.directory / item["name"]
        if not path.exists() or path.stat().st_size != item["bytes"]:
            raise SystemExit(f"Missing or wrong size: {path}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(16 * 1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != item["sha256"]:
            raise SystemExit(f"SHA256 mismatch: {path}")
        print(f"OK {item['name']}", flush=True)


if __name__ == "__main__":
    main()
