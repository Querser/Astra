"""Add quarantine and synthetic scenario provenance.

Revision ID: 0002_ingestion_and_scenarios
Revises: 0001_initial_schema
"""

from alembic import op

from app.models import Base, IngestionRecord, ScenarioRun

revision = "0002_ingestion_and_scenarios"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(), tables=[IngestionRecord.__table__, ScenarioRun.__table__]
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(), tables=[ScenarioRun.__table__, IngestionRecord.__table__]
    )
