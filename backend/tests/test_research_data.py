"""Regression checks for packaged public NASA data, without touching user records."""

import csv
from hashlib import sha256
import json
from pathlib import Path
import shutil

import pytest

from app.db import Database, sqlite_url, upgrade_database
from app.research_data import DATA_DIR, import_packaged_snapshots, parse_osd_575, parse_radlab


def _copied_snapshot(tmp_path: Path) -> Path:
    for filename in ("manifest.json", "radlab_iss_dostel1_2022-04-01.csv",
                     "LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv"):
        shutil.copy2(DATA_DIR / filename, tmp_path / filename)
    return tmp_path


def _replace_csv(directory: Path, section: str, lines: list[str]) -> None:
    meta_path = directory / "manifest.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    path = directory / meta[section]["file"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    meta[section]["sha256"] = sha256(path.read_bytes()).hexdigest()
    meta_path.write_text(json.dumps(meta), encoding="utf-8")


def test_packaged_snapshots_preserve_units_missingness_and_subject_boundary():
    rad, points = parse_radlab()
    lab, observations = parse_osd_575()
    assert len(points) == 84 and rad["unit"]["absorbed_dose_rate"] == "µGy/hour"
    assert rad["missing_equivalent_count"] == 84
    assert rad["sampling_seconds"]["minimum"] != rad["sampling_seconds"]["maximum"]
    assert len(observations) == 532 and len(lab["participants"]) == 4
    assert any(item["missing"] and item["value"] is None for item in observations)
    assert {item["unit"] for item in observations} >= {"mg/dL", "mmol/L", "U/L"}
    assert all(item["participant_id"].startswith("C00") for item in observations)
    assert {item["timepoint"] for item in observations} == {"L-92", "L-44", "L-3", "R+1", "R+45", "R+82", "R+194"}


def test_repeat_import_does_not_duplicate(tmp_path):
    url = sqlite_url(tmp_path / "research.sqlite3")
    upgrade_database(url)
    db = Database(url)
    try:
        with db.session_factory() as session:
            first = import_packaged_snapshots(session)
            second = import_packaged_snapshots(session)
        assert first == {"radlab_total": 84, "lab_total": 532, "radlab_inserted": 84, "lab_inserted": 532}
        assert second["radlab_inserted"] == second["lab_inserted"] == 0
    finally:
        db.dispose()


def test_bad_unit_column_is_rejected(tmp_path):
    directory = _copied_snapshot(tmp_path)
    name = json.loads((directory / "manifest.json").read_text())["osd_575"]["file"]
    lines = (directory / name).read_text(encoding="utf-8-sig").splitlines()
    lines[0] = lines[0].replace("glucose_value_milligram_per_deciliter", "glucose_value_unknown_unit")
    _replace_csv(directory, "osd_575", lines)
    with pytest.raises(ValueError, match="unknown analyte unit"):
        parse_osd_575(directory)


def test_duplicate_and_bad_radlab_values_are_rejected(tmp_path):
    directory = _copied_snapshot(tmp_path)
    name = json.loads((directory / "manifest.json").read_text())["radlab"]["file"]
    lines = (directory / name).read_text(encoding="utf-8-sig").splitlines()
    _replace_csv(directory, "radlab", lines + [lines[1]])
    with pytest.raises(ValueError, match="duplicate"):
        parse_radlab(directory)
    lines[1] = lines[1].replace("9.815504", "NaN")
    _replace_csv(directory, "radlab", lines)
    with pytest.raises(ValueError, match="non-finite"):
        parse_radlab(directory)
