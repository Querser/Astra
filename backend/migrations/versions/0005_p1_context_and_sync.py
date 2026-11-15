"""Add P1 context, simulation, handoff and local sync records.

Revision ID: 0005_p1_context_and_sync
Revises: 0004_forecasts
"""
from alembic import op
from app.models import Base, EmergencyHandoff, EnvironmentalMeasurement, PsychologicalAssessment, SyncEvent, WhatIfScenario

revision = "0005_p1_context_and_sync"
down_revision = "0004_forecasts"
branch_labels = None
depends_on = None

def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind(), tables=[PsychologicalAssessment.__table__, EnvironmentalMeasurement.__table__, WhatIfScenario.__table__, EmergencyHandoff.__table__, SyncEvent.__table__])

def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind(), tables=[SyncEvent.__table__, EmergencyHandoff.__table__, WhatIfScenario.__table__, EnvironmentalMeasurement.__table__, PsychologicalAssessment.__table__])
