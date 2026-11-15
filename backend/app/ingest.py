"""CSV parsing boundary. Parsed content is data, never application instructions."""

import csv
from dataclasses import dataclass
import hashlib
import io
import json

from pydantic import ValidationError

from app.schemas import ObservationData

REQUIRED_COLUMNS = {
    "metric",
    "value_kind",
    "amount",
    "systolic",
    "diastolic",
    "unit",
    "observed_at",
    "synthetic",
    "quality_flags",
}
MAX_IMPORT_ROWS = 1_000


@dataclass(frozen=True)
class QuarantinedRow:
    row_number: int
    reason: str
    content_sha256: str


@dataclass(frozen=True)
class CsvParseResult:
    observations: list[ObservationData]
    quarantined_rows: list[QuarantinedRow]


def fingerprint(row: object) -> str:
    normalized = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError("synthetic must be true or false")


def parse_observation_csv(content: str, source_id: str) -> CsvParseResult:
    """Parse a bounded CSV into valid contracts and redacted quarantine records."""

    reader = csv.DictReader(io.StringIO(content))
    headers = set(reader.fieldnames or [])
    missing_columns = REQUIRED_COLUMNS - headers
    if missing_columns:
        return CsvParseResult(
            observations=[],
            quarantined_rows=[
                QuarantinedRow(
                    row_number=1,
                    reason=f"Required CSV columns are missing: {', '.join(sorted(missing_columns))}.",
                    content_sha256=fingerprint(reader.fieldnames or []),
                )
            ],
        )

    observations: list[ObservationData] = []
    quarantined_rows: list[QuarantinedRow] = []
    for row_number, row in enumerate(reader, start=2):
        if row_number > MAX_IMPORT_ROWS + 1:
            quarantined_rows.append(
                QuarantinedRow(
                    row_number=row_number,
                    reason=f"Import exceeds the {MAX_IMPORT_ROWS}-row limit.",
                    content_sha256=fingerprint(row),
                )
            )
            break
        try:
            kind = (row.get("value_kind") or "").strip()
            if kind == "scalar":
                value: dict[str, object] = {"kind": "scalar", "amount": row.get("amount")}
            elif kind == "blood_pressure":
                value = {
                    "kind": "blood_pressure",
                    "systolic": row.get("systolic"),
                    "diastolic": row.get("diastolic"),
                }
            else:
                raise ValueError("value_kind must be scalar or blood_pressure")
            flags = [item.strip() for item in (row.get("quality_flags") or "").split("|") if item.strip()]
            observations.append(
                ObservationData.model_validate(
                    {
                        "metric": row.get("metric"),
                        "value": value,
                        "unit": row.get("unit"),
                        "observed_at": row.get("observed_at"),
                        "source_id": source_id,
                        "synthetic": parse_bool(row.get("synthetic") or ""),
                        "quality_flags": flags,
                    }
                )
            )
        except (ValidationError, ValueError, TypeError):
            quarantined_rows.append(
                QuarantinedRow(
                    row_number=row_number,
                    reason="Row failed structural validation.",
                    content_sha256=fingerprint(row),
                )
            )
    return CsvParseResult(observations=observations, quarantined_rows=quarantined_rows)
