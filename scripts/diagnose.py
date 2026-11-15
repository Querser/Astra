"""Report local ASTRA runtime readiness without printing private data."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import sqlite3
import subprocess
import sys
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
MODEL = os.environ.get("ASTRA_OLLAMA_MODEL", "qwen3:8b")
OLLAMA_URL = os.environ.get("ASTRA_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
BACKEND_URL = os.environ.get("ASTRA_BACKEND_URL", "http://127.0.0.1:8000")
FRONTEND_URL = os.environ.get("ASTRA_FRONTEND_URL", "http://127.0.0.1:5173")


def command_version(command: list[str]) -> str | None:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    output = (result.stdout or result.stderr).strip().splitlines()
    return output[0] if output else None


def fetch_json(url: str) -> dict | None:
    try:
        with urlopen(url, timeout=2) as response:  # noqa: S310 - loopback URLs only
            return json.loads(response.read().decode("utf-8"))
    except (OSError, URLError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    data_dir = Path(os.environ.get("ASTRA_DATA_DIR") or Path.home() / ".astra" / "data")
    database_path = data_dir / "astra.sqlite3"
    database_ready = False
    if database_path.exists():
        try:
            with sqlite3.connect(database_path) as connection:
                database_ready = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='alembic_version'"
                ).fetchone() is not None
        except sqlite3.Error:
            database_ready = False

    ollama = fetch_json(f"{OLLAMA_URL}/api/tags")
    model_names = [item.get("name", "") for item in (ollama or {}).get("models", [])]
    model_ready = any(name == MODEL or name.startswith(f"{MODEL}:") for name in model_names)
    backend = fetch_json(f"{BACKEND_URL}/api/v1/health")

    report = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "python_executable": sys.executable,
        "node": command_version(["node", "--version"]),
        "npm": command_version(["npm.cmd" if os.name == "nt" else "npm", "--version"]),
        "backend_dependencies": importlib.util.find_spec("fastapi") is not None,
        "frontend_dependencies": (ROOT / "frontend" / "node_modules").is_dir(),
        "database": str(database_path),
        "database_ready": database_ready,
        "ollama_url": OLLAMA_URL,
        "ollama_ready": ollama is not None,
        "configured_model": MODEL,
        "model_ready": model_ready,
        "offline_mode": not model_ready,
        "backend_url": BACKEND_URL,
        "backend_ready": bool(backend and backend.get("status") == "ready"),
        "frontend_url": FRONTEND_URL,
        "logs": str(data_dir / "logs"),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        width = max(map(len, report))
        for key, value in report.items():
            print(f"{key.replace('_', ' ').title():<{width + 2}}{value}")

    required = report["backend_dependencies"] and report["frontend_dependencies"] and report["database_ready"]
    if args.strict and not (required and model_ready):
        return 1
    return 0 if required else 2


if __name__ == "__main__":
    raise SystemExit(main())
