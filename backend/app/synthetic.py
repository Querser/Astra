"""Deterministic, deliberately non-clinical synthetic scenario generator."""

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import hashlib
import json
import random

from app.schemas import ScenarioKind

GENERATOR_VERSION = "1.0"


@dataclass(frozen=True)
class GeneratedObservation:
    metric: str
    value: dict[str, float | str]
    unit: str
    observed_at: datetime
    quality_flags: list[str]


@dataclass(frozen=True)
class GeneratedSymptom:
    description: str
    observed_at: datetime


@dataclass(frozen=True)
class QuarantinePlan:
    filename: str
    row_number: int
    reason: str
    content_sha256: str


@dataclass(frozen=True)
class ScenarioPlan:
    observations: list[GeneratedObservation]
    symptoms: list[GeneratedSymptom]
    quarantines: list[QuarantinePlan]
    declared_urgent: bool

    def fingerprint(self) -> str:
        payload = {
            "observations": [asdict(item) for item in self.observations],
            "symptoms": [asdict(item) for item in self.symptoms],
            "quarantines": [asdict(item) for item in self.quarantines],
            "declared_urgent": self.declared_urgent,
        }
        normalized = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def generate_scenario(kind: ScenarioKind, seed: int, start_at: datetime) -> ScenarioPlan:
    """Generate a stable event plan from a scenario name, seed, and start instant.

    Values illustrate software flow only. They have no clinical threshold or validity claim.
    """

    rng = random.Random(seed)
    base_flags = ["synthetic", "demonstration_only"]
    if kind == ScenarioKind.NORMAL:
        observations = [
            GeneratedObservation(
                metric="heart_rate",
                value={"kind": "scalar", "amount": float(68 + rng.randint(-3, 3))},
                unit="bpm",
                observed_at=start_at + timedelta(hours=index * 6),
                quality_flags=base_flags,
            )
            for index in range(3)
        ]
        return ScenarioPlan(observations, [], [], False)

    if kind == ScenarioKind.GRADUAL_CHANGE:
        base = 62 + rng.randint(-2, 2)
        observations = [
            GeneratedObservation(
                metric="heart_rate",
                value={"kind": "scalar", "amount": float(base + index * 3)},
                unit="bpm",
                observed_at=start_at + timedelta(hours=index * 12),
                quality_flags=base_flags + ["demonstrative_gradual_change"],
            )
            for index in range(4)
        ]
        return ScenarioPlan(observations, [], [], False)

    if kind == ScenarioKind.MISSING_OR_CORRUPT:
        raw_marker = f"missing-or-corrupt|{seed}|{start_at.isoformat()}"
        return ScenarioPlan(
            [],
            [],
            [
                QuarantinePlan(
                    filename="synthetic-missing-or-corrupt.csv",
                    row_number=2,
                    reason="Demonstration scenario emitted a deliberately incomplete record.",
                    content_sha256=hashlib.sha256(raw_marker.encode("utf-8")).hexdigest(),
                )
            ],
            False,
        )

    if kind == ScenarioKind.OPERATOR_DECLARED_URGENT:
        return ScenarioPlan(
            [
                GeneratedObservation(
                    metric="heart_rate",
                    value={"kind": "scalar", "amount": float(70 + rng.randint(-2, 2))},
                    unit="bpm",
                    observed_at=start_at,
                    quality_flags=base_flags + ["operator_declared_urgent_demo"],
                )
            ],
            [
                GeneratedSymptom(
                    description=(
                        "Synthetic operator-declared urgent handoff demonstration. "
                        "Clinical significance is not established."
                    ),
                    observed_at=start_at,
                )
            ],
            [],
            True,
        )

    raise ValueError(f"Unsupported scenario: {kind}")
