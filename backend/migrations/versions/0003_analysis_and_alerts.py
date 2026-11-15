"""Add deterministic analysis results and review alerts.

Revision ID: 0003_analysis_and_alerts
Revises: 0002_ingestion_and_scenarios
"""

from alembic import op

from app.models import Alert, AnalysisResult, Base

revision = "0003_analysis_and_alerts"
down_revision = "0002_ingestion_and_scenarios"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[AnalysisResult.__table__, Alert.__table__])


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[Alert.__table__, AnalysisResult.__table__])
