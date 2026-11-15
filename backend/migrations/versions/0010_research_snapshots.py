"""Keep public research and instrument observations separate from crew records."""

import sqlalchemy as sa
from alembic import op

revision = "0010_research_snapshots"
down_revision = "0009_profile_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_radlab_points",
        sa.Column("record_key", sa.String(64), primary_key=True),
        sa.Column("instrument_id", sa.String(80), nullable=False),
        sa.Column("spacecraft", sa.String(80), nullable=False),
        sa.Column("module", sa.String(80), nullable=True),
        sa.Column("observed_at", sa.DateTime, nullable=False),
        sa.Column("absorbed_dose_rate", sa.Float, nullable=True),
        sa.Column("dose_equivalent_rate", sa.Float, nullable=True),
        sa.Column("source_sha256", sa.String(64), nullable=False),
    )
    op.create_index("ix_research_radlab_time", "research_radlab_points", ["observed_at"])
    op.create_table(
        "research_lab_observations",
        sa.Column("record_key", sa.String(64), primary_key=True),
        sa.Column("participant_id", sa.String(30), nullable=False),
        sa.Column("specimen", sa.String(60), nullable=False),
        sa.Column("timepoint", sa.String(20), nullable=False),
        sa.Column("analyte", sa.String(150), nullable=False),
        sa.Column("original_name", sa.String(200), nullable=False),
        sa.Column("value", sa.Float, nullable=True),
        sa.Column("missing", sa.Boolean, nullable=False),
        sa.Column("unit", sa.String(80), nullable=False),
        sa.Column("reference_low", sa.Float, nullable=True),
        sa.Column("reference_high", sa.Float, nullable=True),
        sa.Column("source_sha256", sa.String(64), nullable=False),
    )
    op.create_index("ix_research_lab_participant", "research_lab_observations", ["participant_id"])


def downgrade() -> None:
    op.drop_index("ix_research_lab_participant", table_name="research_lab_observations")
    op.drop_table("research_lab_observations")
    op.drop_index("ix_research_radlab_time", table_name="research_radlab_points")
    op.drop_table("research_radlab_points")
