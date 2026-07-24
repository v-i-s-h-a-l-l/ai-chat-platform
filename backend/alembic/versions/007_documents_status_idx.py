"""add composite index on documents (project_id, status, updated_at)

Revision ID: 007_documents_status_idx
Revises: 006_create_documents
Create Date: 2026-07-24

"""
from typing import Sequence, Union

from alembic import op

revision: str = "007_documents_status_idx"
down_revision: Union[str, None] = "006_create_documents"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_documents_project_status_updated",
        "documents",
        ["project_id", "status", "updated_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_documents_project_status_updated", table_name="documents")
