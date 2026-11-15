"""Retain optional collection conditions for personal observations."""

import sqlalchemy as sa
from alembic import op


revision = "0011_measurement_context"
down_revision = "0010_research_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("observations")}
    if "measurement_context_json" not in columns:
        op.add_column(
            "observations",
            sa.Column("measurement_context_json", sa.Text(), nullable=False, server_default="{}"),
        )


def downgrade() -> None:
    columns = {item["name"] for item in sa.inspect(op.get_bind()).get_columns("observations")}
    if "measurement_context_json" in columns:
        op.drop_column("observations", "measurement_context_json")
