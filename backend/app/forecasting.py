"""Local horizon-specific forecasts for measured scalar signals, not diagnoses."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from math import isfinite
from statistics import median
from typing import Iterable

from app.models import Observation

HORIZONS = (24, 72, 168)
MIN_FORECAST_POINTS = 8
MIN_TRAIN_POINTS = 4
MIN_EVALUATION_PAIRS = 4
MIN_INTERVAL_PAIRS = 10
HORIZON_LABELS = {24: "24 hours", 72: "72 hours", 168: "7 days"}
METHOD_LABELS = {"persistence": "Last measured value", "recent_median": "Median of the seven most recent measurements", "robust_trend": "Stable trend of the last ten measurements"}
CANONICAL_UNITS = {
    "heart_rate": "bpm", "spo2": "%", "body_temperature": "°C",
    "respiratory_rate": "breaths/min", "sleep_duration": "h",
    "sleep_quality": "score", "activity": "steps", "exertion_fatigue": "score",
}
PROVENANCE_FLAGS = {
    "synthetic_ui_entry", "synthetic", "demo", "demonstration_only",
    "demonstrative_gradual_change", "operator_declared_urgent_demo", "imported",
}


@dataclass(frozen=True)
class ForecastPlan:
    # Original fields remain for older callers. New consumers use horizon_*.
    status: str
    method: str | None
    unit: str | None
    training_count: int
    evaluation_mae: float | None
    baseline_mae: float | None
    interval_coverage: float | None
    interval_radius: float | None
    input_ids: list[str]
    reason: str | None
    predictions: dict[int, float]
    horizon_status: dict[int, str] = field(default_factory=dict)
    horizon_reasons: dict[int, str | None] = field(default_factory=dict)
    horizon_methods: dict[int, str | None] = field(default_factory=dict)
    horizon_mae: dict[int, float | None] = field(default_factory=dict)
    horizon_baseline_mae: dict[int, float | None] = field(default_factory=dict)
    horizon_interval_radius: dict[int, float | None] = field(default_factory=dict)
    horizon_interval_low: dict[int, float | None] = field(default_factory=dict)
    horizon_interval_high: dict[int, float | None] = field(default_factory=dict)
    horizon_interval_coverage: dict[int, float | None] = field(default_factory=dict)
    horizon_evaluation_count: dict[int, int] = field(default_factory=dict)
    history_start_at: datetime | None = None
    history_end_at: datetime | None = None
    history_span_hours: float = 0.0
    excluded_count: int = 0
    synthetic_count: int = 0
    recent_values: list[float] = field(default_factory=list)
    horizon_selection_errors: dict[int, dict[str, float]] = field(default_factory=dict)


def _utc(value: datetime) -> datetime:
    """SQLite persists UTC without tzinfo; normalize offset-aware callers too."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def scalar_series(observations: Iterable[Observation]) -> list[Observation]:
    return sorted(
        [item for item in observations if item.value_kind == "scalar" and item.scalar_value is not None],
        key=lambda item: (_utc(item.observed_at), item.id),
    )


def baseline_profile(observations: Iterable[Observation]) -> dict[str, float | int | None]:
    series = scalar_series(observations)
    if not series:
        return {"count": 0, "median": None, "mad": None}
    values = [item.scalar_value for item in series if item.scalar_value is not None]
    center = median(values)
    return {"count": len(values), "median": center, "mad": median([abs(value - center) for value in values])}


def linear_predict(training: list[Observation], target_at: datetime) -> float:
    start = _utc(training[0].observed_at)
    x_values = [(_utc(item.observed_at) - start).total_seconds() / 3600 for item in training]
    y_values = [float(item.scalar_value) for item in training]
    x_center = sum(x_values) / len(x_values)
    y_center = sum(y_values) / len(y_values)
    denominator = sum((value - x_center) ** 2 for value in x_values)
    if denominator == 0:
        return y_values[-1]
    slope = sum((x - x_center) * (y - y_center) for x, y in zip(x_values, y_values)) / denominator
    target_x = (_utc(target_at) - start).total_seconds() / 3600
    return y_center + slope * (target_x - x_center)


def _predict(training: list[Observation], target_at: datetime, method: str) -> float:
    if method == "persistence":
        return float(training[-1].scalar_value)
    if method == "recent_median":
        return float(median(float(item.scalar_value) for item in training[-7:]))
    if method == "robust_trend":
        recent = training[-10:]
        end = _utc(recent[-1].observed_at)
        slopes = []
        for earlier_index, earlier in enumerate(recent):
            for later in recent[earlier_index + 1:]:
                hours = (_utc(later.observed_at) - _utc(earlier.observed_at)).total_seconds() / 3600
                if hours > 0:
                    slopes.append((float(later.scalar_value) - float(earlier.scalar_value)) / hours)
        slope = float(median(slopes)) if slopes else 0.0
        center = float(median(float(item.scalar_value) for item in recent[-3:]))
        elapsed = (_utc(target_at) - end).total_seconds() / 3600
        return center + slope * elapsed
    raise ValueError(f"Unknown forecast method: {method}")


def _valid_scalar(item: Observation) -> bool:
    value = item.scalar_value
    if value is None or not isfinite(float(value)) or set(item.quality_flags) - PROVENANCE_FLAGS:
        return False
    if item.metric == "spo2":
        return 0 <= value <= 100
    if item.metric in {"heart_rate", "respiratory_rate"}:
        return value > 0
    if item.metric in {"sleep_quality", "exertion_fatigue"}:
        return 0 <= value <= 10
    if item.metric in {"sleep_duration", "activity"}:
        return value >= 0
    return True


def _valid_prediction(metric: str, value: float) -> bool:
    if not isfinite(value):
        return False
    if metric == "spo2":
        return 0 <= value <= 100
    if metric in {"heart_rate", "respiratory_rate"}:
        return value > 0
    if metric == "sleep_duration":
        return 0 <= value <= 24
    if metric in {"sleep_quality", "exertion_fatigue"}:
        return 0 <= value <= 10
    if metric in {"sleep_quality", "activity", "exertion_fatigue"}:
        return value >= 0
    return True


def _bounded_interval(metric: str, prediction: float, radius: float) -> tuple[float, float]:
    low, high = prediction - radius, prediction + radius
    if metric in {"heart_rate", "respiratory_rate", "sleep_duration", "sleep_quality", "activity", "exertion_fatigue", "spo2"}:
        low = max(0.0, low)
    if metric == "spo2":
        high = min(100.0, high)
    if metric == "sleep_duration":
        high = min(24.0, high)
    if metric in {"sleep_quality", "exertion_fatigue"}:
        high = min(10.0, high)
    return low, high


def _mae(errors: list[float]) -> float:
    return sum(errors) / len(errors)


def _errors(series: list[Observation], pairs: list[tuple[int, int]], method: str) -> list[float]:
    errors: list[float] = []
    for origin, target in pairs:
        training = series[:origin + 1]
        predicted = _predict(training, series[target].observed_at, method)
        errors.append(abs(float(series[target].scalar_value) - predicted))
    return errors


def _evaluation_pairs(series: list[Observation], horizon: int) -> list[tuple[int, int]]:
    """Match actuals near each horizon; the next sample is not a 7-day holdout."""
    tolerance = timedelta(hours=min(24, horizon * 0.2))
    pairs: list[tuple[int, int]] = []
    for origin in range(MIN_TRAIN_POINTS - 1, len(series) - 1):
        target_at = _utc(series[origin].observed_at) + timedelta(hours=horizon)
        candidates = [
            target for target in range(origin + 1, len(series))
            if abs(_utc(series[target].observed_at) - target_at) <= tolerance
        ]
        if candidates:
            target = min(candidates, key=lambda index: abs(_utc(series[index].observed_at) - target_at))
            pairs.append((origin, target))
    return pairs


def _refused(series: list[Observation], reason: str, unit: str | None, excluded: int, synthetic: int) -> ForecastPlan:
    start = _utc(series[0].observed_at) if series else None
    end = _utc(series[-1].observed_at) if series else None
    return ForecastPlan(
        "insufficient", None, unit, len(series), None, None, None, None,
        [item.id for item in series], reason, {},
        horizon_status={h: "insufficient" for h in HORIZONS},
        horizon_reasons={h: f"Forecast for {HORIZON_LABELS[h]}: {reason}" for h in HORIZONS},
        horizon_methods={h: None for h in HORIZONS},
        horizon_mae={h: None for h in HORIZONS},
        horizon_baseline_mae={h: None for h in HORIZONS},
        horizon_interval_radius={h: None for h in HORIZONS},
        horizon_interval_low={h: None for h in HORIZONS},
        horizon_interval_high={h: None for h in HORIZONS},
        horizon_interval_coverage={h: None for h in HORIZONS},
        horizon_evaluation_count={h: 0 for h in HORIZONS},
        history_start_at=start, history_end_at=end,
        history_span_hours=(end - start).total_seconds() / 3600 if start and end else 0.0,
        excluded_count=excluded, synthetic_count=synthetic,
    )


def forecast_series(observations: Iterable[Observation]) -> ForecastPlan:
    raw = list(observations)
    scalar = scalar_series(raw)
    series = [item for item in scalar if _valid_scalar(item)]
    excluded = len(raw) - len(series)
    synthetic = sum(item.synthetic for item in series)
    unit = series[-1].unit if series else scalar[-1].unit if scalar else None
    metric_names = {item.metric for item in raw}
    if len(metric_names) != 1:
        return _refused(series, "A series of one indicator is needed.", unit, excluded, synthetic)
    metric = next(iter(metric_names))
    if metric not in CANONICAL_UNITS:
        return _refused(series, "No statistical forecast is set up for this indicator.", unit, excluded, synthetic)
    if not scalar:
        return _refused(series, "There are no scalar measurements for this indicator.", unit, excluded, synthetic)
    if scalar[-1] not in series:
        return _refused(series, "The last record is marked as unreliable or unsuitable for calculation; a new verified record is needed.", unit, excluded, synthetic)
    if len({item.unit for item in series}) != 1 or unit != CANONICAL_UNITS[metric]:
        return _refused(series, "Units of measurement differ or do not match the supported unit; calculation is not possible without a verified conversion.", unit, excluded, synthetic)
    if len({_utc(item.observed_at) for item in series}) != len(series):
        return _refused(series, "There are multiple measurements of one indicator at the same time; please clarify or correct the records.", unit, excluded, synthetic)
    if len(series) < MIN_FORECAST_POINTS:
        return _refused(series, f"At least {MIN_FORECAST_POINTS} suitable measurements are needed; currently {len(series)}. Excluded by quality or type: {excluded}.", unit, excluded, synthetic)

    start, end = _utc(series[0].observed_at), _utc(series[-1].observed_at)
    status: dict[int, str] = {}
    reasons: dict[int, str | None] = {}
    methods: dict[int, str | None] = {}
    mae: dict[int, float | None] = {}
    baseline_mae: dict[int, float | None] = {}
    radii: dict[int, float | None] = {}
    interval_low: dict[int, float | None] = {}
    interval_high: dict[int, float | None] = {}
    coverage: dict[int, float | None] = {}
    evaluation_count: dict[int, int] = {}
    predictions: dict[int, float] = {}
    selection_scores: dict[int, dict[str, float]] = {}

    for horizon in HORIZONS:
        pairs = _evaluation_pairs(series, horizon)
        evaluation_count[horizon] = 0
        methods[horizon] = None
        mae[horizon] = baseline_mae[horizon] = None
        radii[horizon] = interval_low[horizon] = interval_high[horizon] = coverage[horizon] = None
        if len(pairs) < MIN_EVALUATION_PAIRS:
            status[horizon] = "insufficient"
            reasons[horizon] = (
                f"The {HORIZON_LABELS[horizon]} horizon needs at least {MIN_EVALUATION_PAIRS} "
                f"chronological pairs of measurements with approximately such an interval; found {len(pairs)}. "
                "Continue comparable measurements and repeat the calculation."
            )
            continue

        if len(pairs) >= MIN_INTERVAL_PAIRS:
            test_count = max(3, len(pairs) // 4)
            selection_end = len(pairs) - test_count
            selection_start = max(0, selection_end - 12)
            selection = pairs[selection_start:selection_end]
            calibration = pairs[:selection_start] if selection_start >= 3 else []
            test = pairs[selection_end:]
        else:
            select_end = len(pairs) // 2
            selection, calibration, test = pairs[:select_end], [], pairs[select_end:]
        selection_errors = {candidate: _mae(_errors(series, selection, candidate))
                            for candidate in ("persistence", "recent_median", "robust_trend")}
        method = min(selection_errors, key=selection_errors.get)
        selection_scores[horizon] = selection_errors
        prediction = _predict(series, end + timedelta(hours=horizon), method)
        if not _valid_prediction(metric, prediction):
            method = "recent_median"
            prediction = _predict(series, end + timedelta(hours=horizon), method)
        if not _valid_prediction(metric, prediction):
            status[horizon] = "insufficient"
            reasons[horizon] = "Calculation gives a physically impossible value; check history and method is required."
            continue

        selected_errors = _errors(series, test, method)
        baseline_errors = _errors(series, test, "persistence")
        evaluation_count[horizon] = len(test)
        methods[horizon] = method
        mae[horizon] = _mae(selected_errors)
        baseline_mae[horizon] = _mae(baseline_errors)
        if calibration:
            radius = max(_errors(series, calibration, method))
            if radius > 0:
                radii[horizon] = radius
                interval_low[horizon], interval_high[horizon] = _bounded_interval(metric, prediction, radius)
                coverage[horizon] = sum(error <= radius for error in selected_errors) / len(selected_errors)
        status[horizon], reasons[horizon], predictions[horizon] = "available", None, prediction

    first = next((h for h in HORIZONS if status[h] == "available"), None)
    return ForecastPlan(
        "available" if first is not None else "insufficient",
        methods[first] if first is not None else None,
        unit, len(series), mae[first] if first is not None else None,
        baseline_mae[first] if first is not None else None,
        coverage[first] if first is not None else None,
        radii[first] if first is not None else None,
        [item.id for item in series], None if first is not None else reasons[HORIZONS[0]], predictions,
        horizon_status=status, horizon_reasons=reasons, horizon_methods=methods,
        horizon_mae=mae, horizon_baseline_mae=baseline_mae,
        horizon_interval_radius=radii, horizon_interval_low=interval_low,
        horizon_interval_high=interval_high, horizon_interval_coverage=coverage,
        horizon_evaluation_count=evaluation_count,
        history_start_at=start, history_end_at=end,
        history_span_hours=(end - start).total_seconds() / 3600,
        excluded_count=excluded, synthetic_count=synthetic,
        recent_values=[float(item.scalar_value) for item in series[-8:]],
        horizon_selection_errors=selection_scores,
    )
