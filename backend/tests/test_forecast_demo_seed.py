"""Varied fictional series demonstrate horizon-dependent predictions."""

from sqlalchemy import select

from app.db import Database, sqlite_url, upgrade_database
from app.forecast_demo_seed import GRADUAL_NAME, seed_forecast_profiles
from app.forecasting import forecast_series
from app.models import CrewMember, Observation


def test_varied_forecast_profiles_are_idempotent_and_change_by_horizon(tmp_path):
    url = sqlite_url(tmp_path / "varied.sqlite3")
    upgrade_database(url)
    database = Database(url)
    try:
        with database.session_factory() as session:
            first = seed_forecast_profiles(session)
            assert all(count == 28 * 8 for count in first.values())
            assert all(count == 0 for count in seed_forecast_profiles(session).values())
            crew = session.scalar(select(CrewMember).where(CrewMember.display_name == GRADUAL_NAME))
            series = list(session.scalars(select(Observation).where(
                Observation.crew_member_id == crew.id, Observation.metric == "heart_rate")))
            plan = forecast_series(series)
            assert all(plan.horizon_status[horizon] == "available" for horizon in (24, 72, 168))
            assert plan.predictions[24] != plan.predictions[168]
    finally:
        database.dispose()
