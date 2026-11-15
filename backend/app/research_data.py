"""Validated, offline public research snapshots, isolated from crew observations."""

from __future__ import annotations

import csv
from datetime import datetime
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import re
from statistics import median

from fastapi import APIRouter, Request
from sqlalchemy import text
from sqlalchemy.orm import Session


router = APIRouter(prefix="/research", tags=["research"])
DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "research"

UNIT_SUFFIXES = {
    "gram_per_deciliter": "g/dL",
    "units_per_liter": "U/L",
    "milligram_per_deciliter": "mg/dL",
    "millimol_per_liter": "mmol/L",
    "milliliter_per_minute_per_1.73_meter_squared": "mL/min/1.73 m²",
}


def manifest() -> dict:
    return json.loads((DATA_DIR / "manifest.json").read_text(encoding="utf-8"))


def _verified_rows(section: str, data_dir: Path = DATA_DIR) -> tuple[dict, list[dict[str, str]]]:
    metadata = json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))[section]
    raw = (data_dir / metadata["file"]).read_bytes()
    if sha256(raw).hexdigest() != metadata["sha256"]:
        raise ValueError(f"{section}: snapshot SHA-256 mismatch")
    with (data_dir / metadata["file"]).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError(f"{section}: invalid CSV header")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{section}: empty snapshot")
    return metadata, rows


def _number(raw: str | None) -> float | None:
    if raw is None or raw.strip().upper() in {"", "NA", "N/A", "NULL"}:
        return None
    value = float(raw)
    if not isfinite(value):
        raise ValueError("non-finite research value")
    return value


def _key(*parts: str) -> str:
    return sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def parse_radlab(data_dir: Path = DATA_DIR) -> tuple[dict, list[dict]]:
    meta, rows = _verified_rows("radlab", data_dir)
    required = {"timestamp", "instrument_id", "absorbed_dose_rate", "dose_equivalent_rate", "module", "spacecraft"}
    if not required <= set(rows[0]):
        raise ValueError("RadLab columns missing")
    parsed: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        try:
            stamp = datetime.fromisoformat(row["timestamp"])
        except (TypeError, ValueError) as error:
            raise ValueError("RadLab timestamp invalid") from error
        if row["instrument_id"] != meta["instrument_id"] or row["spacecraft"] != "ISS":
            raise ValueError("RadLab instrument or spacecraft mismatch")
        absorbed = _number(row["absorbed_dose_rate"])
        equivalent = _number(row["dose_equivalent_rate"])
        if absorbed is not None and absorbed < 0 or equivalent is not None and equivalent < 0:
            raise ValueError("negative dose rate")
        key = _key(meta["dataset_id"], meta["version"], row["instrument_id"], row["timestamp"])
        if key in seen:
            raise ValueError("duplicate RadLab point")
        seen.add(key)
        parsed.append({"record_key": key, "timestamp": stamp.isoformat(), "instrument_id": row["instrument_id"],
                       "spacecraft": row["spacecraft"], "module": row["module"] or None,
                       "absorbed_dose_rate": absorbed, "dose_equivalent_rate": equivalent})
    parsed.sort(key=lambda point: point["timestamp"])
    deltas = [(datetime.fromisoformat(right["timestamp"]) - datetime.fromisoformat(left["timestamp"])).total_seconds()
              for left, right in zip(parsed, parsed[1:])]
    if any(delta <= 0 for delta in deltas):
        raise ValueError("RadLab timestamps not strictly increasing")
    meta = {**meta, "retrieved_at": json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))["retrieved_at"],
            "sampling_seconds": {"minimum": min(deltas), "median": median(deltas), "maximum": max(deltas)} if deltas else None,
            "missing_equivalent_count": sum(point["dose_equivalent_rate"] is None for point in parsed)}
    return meta, parsed


def _analyte_columns(columns: list[str]) -> list[tuple[str, str, str, str]]:
    result = []
    for column in columns:
        if "_value" not in column:
            continue
        if column.endswith("_value"):
            analyte, unit_suffix = column[:-6], "ratio"
            low, high = f"{analyte}_range_min", f"{analyte}_range_max"
        else:
            analyte, unit_suffix = column.split("_value_", 1)
            low, high = f"{analyte}_range_min_{unit_suffix}", f"{analyte}_range_max_{unit_suffix}"
        if unit_suffix != "ratio" and unit_suffix not in UNIT_SUFFIXES:
            raise ValueError(f"unknown analyte unit: {column}")
        if analyte in {"alt", "ast"} and high not in columns:
            high = f"{analyte}_max_{unit_suffix}"
        if low not in columns or high not in columns:
            raise ValueError(f"missing reference columns for {column}")
        result.append((column, low, high, unit_suffix))
    return result


def parse_osd_575(data_dir: Path = DATA_DIR) -> tuple[dict, list[dict]]:
    meta, rows = _verified_rows("osd_575", data_dir)
    columns = list(rows[0])
    if "Sample Name" not in columns:
        raise ValueError("OSD-575 Sample Name missing")
    analytes = _analyte_columns(columns)
    parsed: list[dict] = []
    seen: set[str] = set()
    for row in rows:
        match = re.fullmatch(r"(C\d{3})_(serum)_(L-\d+|R\+\d+)", row["Sample Name"])
        if not match:
            raise ValueError("OSD-575 unexpected sample identifier")
        participant_id, specimen, timepoint = match.groups()
        for value_column, low_column, high_column, suffix in analytes:
            value, lower, upper = (_number(row[column]) for column in (value_column, low_column, high_column))
            if lower is not None and upper is not None and lower > upper:
                raise ValueError("OSD-575 inverted reference bounds")
            analyte = value_column.split("_value")[0]
            key = _key(meta["dataset_id"], meta["version"], meta["file"], row["Sample Name"], analyte)
            if key in seen:
                raise ValueError("duplicate OSD-575 observation")
            seen.add(key)
            parsed.append({"record_key": key, "participant_id": participant_id, "specimen": specimen,
                           "timepoint": timepoint, "analyte": analyte, "original_name": value_column,
                           "value": value, "missing": value is None, "unit": UNIT_SUFFIXES.get(suffix, "ratio"),
                           "reference_low": lower, "reference_high": upper})
    meta = {**meta, "retrieved_at": json.loads((data_dir / "manifest.json").read_text(encoding="utf-8"))["retrieved_at"],
            "participants": sorted({row["participant_id"] for row in parsed})}
    return meta, parsed


def import_packaged_snapshots(session: Session) -> dict[str, int]:
    """Validate packaged CSVs and insert only absent stable record keys."""
    rad_meta, rad_points = parse_radlab()
    lab_meta, lab_points = parse_osd_575()
    before = tuple(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() for table in
                   ("research_radlab_points", "research_lab_observations"))
    for point in rad_points:
        session.execute(text("""INSERT OR IGNORE INTO research_radlab_points
            (record_key,instrument_id,spacecraft,module,observed_at,absorbed_dose_rate,dose_equivalent_rate,source_sha256)
            VALUES (:record_key,:instrument_id,:spacecraft,:module,:timestamp,:absorbed_dose_rate,:dose_equivalent_rate,:source_sha256)"""),
            {**point, "source_sha256": rad_meta["sha256"]})
    for item in lab_points:
        session.execute(text("""INSERT OR IGNORE INTO research_lab_observations
            (record_key,participant_id,specimen,timepoint,analyte,original_name,value,missing,unit,reference_low,reference_high,source_sha256)
            VALUES (:record_key,:participant_id,:specimen,:timepoint,:analyte,:original_name,:value,:missing,:unit,:reference_low,:reference_high,:source_sha256)"""),
            {**item, "source_sha256": lab_meta["sha256"]})
    session.commit()
    after = tuple(session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one() for table in
                  ("research_radlab_points", "research_lab_observations"))
    return {"radlab_total": after[0], "lab_total": after[1], "radlab_inserted": after[0]-before[0], "lab_inserted": after[1]-before[1]}


@router.get("/radlab")
def get_radlab(request: Request) -> dict:
    meta, _ = parse_radlab()
    with request.app.state.database.session_factory() as session:
        points = [dict(row._mapping) for row in session.execute(text("""SELECT observed_at AS timestamp,
            absorbed_dose_rate,dose_equivalent_rate FROM research_radlab_points
            WHERE source_sha256=:sha ORDER BY observed_at"""), {"sha": meta["sha256"]})]
    return {**meta, "points": points}


@router.get("/osd-575")
def get_osd_575(request: Request) -> dict:
    meta, _ = parse_osd_575()
    with request.app.state.database.session_factory() as session:
        observations = [dict(row._mapping) for row in session.execute(text("""SELECT participant_id,specimen,timepoint,
            analyte,original_name,value,missing,unit,reference_low,reference_high FROM research_lab_observations
            WHERE source_sha256=:sha ORDER BY participant_id,timepoint,analyte"""), {"sha": meta["sha256"]})]
    return {**meta, "observations": observations}


def research_context_for(query: str) -> list[dict[str, str]]:
    """Bounded public context only; no mapping from subjects/instruments to crew."""
    low = query.lower()
    snippets: list[dict[str, str]] = []
    if any(word in low for word in ("\u0440\u0430\u0434\u0438\u0430\u0446", "\u043e\u0431\u043b\u0443\u0447", "\u0434\u043e\u0437", "radlab", "radiation")):
        meta, points = parse_radlab()
        values = [point["absorbed_dose_rate"] for point in points if point["absorbed_dose_rate"] is not None]
        snippets.append({"id": meta["dataset_id"], "source_url": meta["documentation_url"],
                         "text": (f"Local RadLab archive: device {meta['instrument_id']}, location {meta['location']}, "
                                  f"{points[0]['timestamp']}—{points[-1]['timestamp']} (time zone not specified in CSV). "
                                  f"{len(points)} points; absorbed dose power {min(values):.2f}–{max(values):.2f} µGy/hour. "
                                  f"Last entry: {points[-1]['timestamp']}, {points[-1]['absorbed_dose_rate']:.6f} µGy/hour. "
                                  "Equivalent dose power for this sample is not available. This is an environmental measurement by the device, not the crew's personal dose.")})
    if any(word in low for word in ("\u043b\u0430\u0431\u043e\u0440\u0430\u0442\u043e\u0440", "\u0430\u043d\u0430\u043b\u0438\u0437 \u043a\u0440\u043e\u0432\u0438", "\u0431\u0438\u043e\u043c\u0430\u0440\u043a\u0435\u0440", "\u0433\u043b\u044e\u043a\u043e\u0437", "osd-575", "\u043a\u0440\u0435\u0430\u0442\u0438\u043d\u0438\u043d")):
        meta, rows = parse_osd_575()
        snippets.append({"id": "OSD-575-v3-CMP", "source_url": meta["source_url"],
                         "text": (f"Public OSD-575 v{meta['version']} dataset: comprehensive metabolic panel (CMP) on serum samples, 4 anonymized participants, "
                                  "28 samples, points L-92/L-44/L-3 pre-flight and R+1/R+45/R+82/R+194 post-flight."
                                  "These are rare research measurements from other people, not indicators from the selected crew."
                                  "Laboratory limits relate to the initial analysis and method.")})
    return snippets
