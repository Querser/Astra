"""Add cautious statistical forecast persistence.

Revision ID: 0004_forecasts
Revises: 0003_analysis_and_alerts
"""

from alembic import op

from app.models import Base, Forecast

revision = "0004_forecasts"
down_revision = "0003_analysis_and_alerts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[Forecast.__table__])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Forecast.__table__])
