"""add projects.active_document_id for conversation document context

Revision ID: 008_project_active_document
Revises: 007_documents_status_idx
Create Date: 2026-07-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008_project_active_document"
down_revision: Union[str, None] = "007_documents_status_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column(
            "active_document_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_projects_active_document_id",
        "projects",
        "documents",
        ["active_document_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_projects_active_document_id",
        "projects",
        ["active_document_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_projects_active_document_id", table_name="projects")
    op.drop_constraint("fk_projects_active_document_id", "projects", type_="foreignkey")
    op.drop_column("projects", "active_document_id")
