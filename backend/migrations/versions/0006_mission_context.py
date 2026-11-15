"""Associate fictional mission setting and habitat records with crew profiles.

Revision ID: 0006_mission_context
Revises: 0005_p1_context_and_sync
"""
import sqlalchemy as sa
from alembic import op

revision = "0006_mission_context"
down_revision = "0005_p1_context_and_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    crew_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("crew_members")}
    missing = [name for name in ("mission_location", "mission_phase", "habitat") if name not in crew_columns]
    if missing:
        with op.batch_alter_table("crew_members") as batch:
            for name in missing:
                batch.add_column(sa.Column(name, sa.String({"mission_location": 20, "mission_phase": 40, "habitat": 80}[name]), nullable=True))
    environment_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("environmental_measurements")}
    existing_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("environmental_measurements")}
    if "crew_member_id" not in environment_columns or "ix_environmental_measurements_crew_member_id" not in existing_indexes:
        with op.batch_alter_table("environmental_measurements", naming_convention={"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}) as batch:
            if "crew_member_id" not in environment_columns:
                batch.add_column(sa.Column("crew_member_id", sa.String(36), nullable=True))
                batch.create_foreign_key("fk_environmental_measurements_crew_member_id", "crew_members", ["crew_member_id"], ["id"], ondelete="RESTRICT")
            if "ix_environmental_measurements_crew_member_id" not in existing_indexes:
                batch.create_index("ix_environmental_measurements_crew_member_id", ["crew_member_id"])


def downgrade() -> None:
    with op.batch_alter_table("environmental_measurements") as batch:
        batch.drop_index("ix_environmental_measurements_crew_member_id")
        batch.drop_column("crew_member_id")
    with op.batch_alter_table("crew_members") as batch:
        batch.drop_column("habitat")
        batch.drop_column("mission_phase")
        batch.drop_column("mission_location")
