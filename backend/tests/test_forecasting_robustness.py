"""Chronological forecasts remain traceable and robust to one isolated reading."""

from datetime import datetime, timedelta

from app.forecasting import _evaluation_pairs, forecast_series
from app.models import Observation


def test_isolated_spo2_low_does_not_drag_stable_recent_forecast():
    values = [98] * 19 + [91, 98, 98, 97, 99, 98, 97, 98]
    start = datetime(2026, 10, 1, 8)
    observations = [Observation(
        id=str(index), crew_member_id="demo", source_id="demo", metric="spo2",
        value_kind="scalar", scalar_value=float(value), unit="%",
        observed_at=start + timedelta(days=index), observed_offset_minutes=0,
        synthetic=True, quality_flags_json='["synthetic_ui_entry"]',
    ) for index, value in enumerate(values)]
    plan = forecast_series(observations)
    assert plan.recent_values == [91, 98, 98, 97, 99, 98, 97, 98]
    assert all(plan.horizon_status[horizon] == "available" for horizon in (24, 72, 168))
    assert all(97 <= plan.predictions[horizon] <= 99 for horizon in (24, 72, 168))
    assert all(set(plan.horizon_selection_errors[horizon]) == {"persistence", "recent_median", "robust_trend"}
               for horizon in (24, 72, 168))
    assert all(target - origin == 1 for origin, target in _evaluation_pairs(observations, 24))
    assert all(6 <= target - origin <= 7 for origin, target in _evaluation_pairs(observations, 168))
