"""add composite index on chat_messages (project_id, created_at)

Revision ID: 005_chat_msg_composite_idx
Revises: 004_add_web_search_used
Create Date: 2026-07-22

"""
from typing import Sequence, Union

from alembic import op

revision: str = "005_chat_msg_composite_idx"
down_revision: Union[str, None] = "004_add_web_search_used"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_chat_messages_project_id_created_at",
        "chat_messages",
        ["project_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_messages_project_id_created_at", table_name="chat_messages")
