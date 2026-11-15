"""Packaging contracts that protect ASTRA's local-only launch behavior."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def test_required_setup_and_launcher_files_exist() -> None:
    required = (
        "backend/requirements.txt",
        "backend/requirements.lock",
        "frontend/package-lock.json",
        "scripts/setup.ps1",
        "scripts/setup.cmd",
        "scripts/setup.sh",
        "scripts/launch.ps1",
        "scripts/launch.cmd",
        "scripts/launch.sh",
        "scripts/diagnose.py",
        "scripts/initialize.py",
        "Launch_ASTRA.cmd",
        "Launch_ASTRA.ps1",
        "launch_astra.sh",
    )
    missing = [name for name in required if not (ROOT / name).is_file()]
    assert not missing


def test_launchers_bind_only_to_loopback() -> None:
    for name in ("scripts/launch.ps1", "scripts/launch.sh"):
        content = (ROOT / name).read_text(encoding="utf-8")
        assert "127.0.0.1" in content
        assert "0.0.0.0" not in content


def test_model_and_ollama_binaries_are_not_committed() -> None:
    forbidden_suffixes = {".gguf", ".safetensors"}
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    forbidden = [name for name in tracked if Path(name).suffix.casefold() in forbidden_suffixes]
    assert not forbidden
