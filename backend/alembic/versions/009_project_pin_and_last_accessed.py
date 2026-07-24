"""Add is_pinned and last_accessed_at to projects.

Revision ID: 009_project_pin_access
Revises: 008_project_active_document
Create Date: 2026-07-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009_project_pin_access"
down_revision: Union[str, None] = "008_project_active_document"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "projects",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE projects SET last_accessed_at = created_at WHERE last_accessed_at IS NULL")
    op.create_index("ix_projects_user_pinned_accessed", "projects", ["user_id", "is_pinned", "last_accessed_at"])


def downgrade() -> None:
    op.drop_index("ix_projects_user_pinned_accessed", table_name="projects")
    op.drop_column("projects", "last_accessed_at")
    op.drop_column("projects", "is_pinned")
