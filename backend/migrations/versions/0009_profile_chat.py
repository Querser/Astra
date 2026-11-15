"""Store profile-owned dialogue memory and idempotent turn identifiers."""
import sqlalchemy as sa
from alembic import op

revision = "0009_profile_chat"
down_revision = "0008_chat_engine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if "request_id" not in {column["name"] for column in sa.inspect(bind).get_columns("chat_messages")}:
        op.add_column("chat_messages", sa.Column("request_id", sa.String(36)))
    op.create_index("uq_chat_turn_owner_request", "chat_messages", ["crew_member_id", "request_id", "role"], unique=True)
    op.create_table("chat_memory",
                    sa.Column("crew_member_id", sa.String(36), sa.ForeignKey("crew_members.id"), primary_key=True),
                    sa.Column("content_json", sa.Text, nullable=False))


def downgrade() -> None:
    op.drop_table("chat_memory")
    op.drop_index("uq_chat_turn_owner_request", table_name="chat_messages")
    op.drop_column("chat_messages", "request_id")
