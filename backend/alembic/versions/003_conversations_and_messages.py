"""Add conversations and messages tables

Revision ID: 003
Revises: 002
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("topic_id", sa.String(36), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_id", sa.String(36), sa.ForeignKey("entries.id", ondelete="SET NULL"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.add_column(
        "entries",
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_index("ix_conversations_topic_id", "conversations", ["topic_id"])
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_index("ix_messages_entry_id", "messages", ["entry_id"])
    op.create_index("ix_entries_conversation_id", "entries", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_entries_conversation_id", table_name="entries")
    op.drop_index("ix_messages_entry_id", table_name="messages")
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_index("ix_conversations_topic_id", table_name="conversations")

    op.drop_column("entries", "conversation_id")
    op.drop_table("messages")
    op.drop_table("conversations")
