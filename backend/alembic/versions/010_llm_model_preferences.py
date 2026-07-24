"""Add llm_model to projects and preferred_llm_model to users.

Revision ID: 010_llm_model_prefs
Revises: 009_project_pin_access
Create Date: 2026-07-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010_llm_model_prefs"
down_revision: Union[str, None] = "009_project_pin_access"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("projects", sa.Column("llm_model", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("preferred_llm_model", sa.String(length=128), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "preferred_llm_model")
    op.drop_column("projects", "llm_model")
