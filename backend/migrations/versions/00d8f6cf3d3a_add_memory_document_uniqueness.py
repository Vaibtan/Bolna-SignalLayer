"""add_memory_document_uniqueness

Revision ID: 00d8f6cf3d3a
Revises: c96d49dcaa5b
Create Date: 2026-03-14 19:05:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "00d8f6cf3d3a"
down_revision: Union[str, Sequence[str], None] = "c96d49dcaa5b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_memory_documents_call_session_doc_type",
        "memory_documents",
        ["call_session_id", "doc_type"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_memory_documents_call_session_doc_type",
        "memory_documents",
        type_="unique",
    )
