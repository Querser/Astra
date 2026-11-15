"""Persist local assistant conversation turns.

Revision ID: 0007_assistant_chat
Revises: 0006_mission_context
"""
import sqlalchemy as sa
from alembic import op

revision = "0007_assistant_chat"
down_revision = "0006_mission_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("crew_member_id", sa.String(36), sa.ForeignKey("crew_members.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("role", sa.String(16), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("source_report_id", sa.String(36), sa.ForeignKey("symptom_reports.id", ondelete="RESTRICT")),
            sa.Column("analysis_result_id", sa.String(36), sa.ForeignKey("analysis_results.id", ondelete="RESTRICT")),
            sa.Column("citations_json", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_chat_messages_crew_member_id", "chat_messages", ["crew_member_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_crew_member_id", table_name="chat_messages")
    op.drop_table("chat_messages")
