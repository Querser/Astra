"""Record whether an answer used local model extraction or offline rules.

Revision ID: 0008_chat_engine
Revises: 0007_assistant_chat
"""
import sqlalchemy as sa
from alembic import op

revision = "0008_chat_engine"
down_revision = "0007_assistant_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("chat_messages")}
    if "engine" not in columns:
        op.add_column("chat_messages", sa.Column("engine", sa.String(100), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "engine")
