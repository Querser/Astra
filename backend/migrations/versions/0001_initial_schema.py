"""Create the Stage 2 local record schema.

Revision ID: 0001_initial_schema
Revises: None
"""

from alembic import op

from app.models import AuditEvent, Base, CrewMember, DataSource, Observation, SymptomReport

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(
        bind=op.get_bind(),
        tables=[
            CrewMember.__table__,
            DataSource.__table__,
            Observation.__table__,
            SymptomReport.__table__,
            AuditEvent.__table__,
        ],
    )


def downgrade() -> None:
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[
            AuditEvent.__table__,
            SymptomReport.__table__,
            Observation.__table__,
            DataSource.__table__,
            CrewMember.__table__,
        ],
    )
