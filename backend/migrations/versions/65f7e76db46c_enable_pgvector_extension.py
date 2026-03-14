"""enable_pgvector_extension

Revision ID: 65f7e76db46c
Revises: f6d9f4e1c2ab
Create Date: 2026-03-14 15:48:22.530681

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '65f7e76db46c'
down_revision: Union[str, Sequence[str], None] = 'f6d9f4e1c2ab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Enable the pgvector extension."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Remove the pgvector extension."""
    op.execute("DROP EXTENSION IF EXISTS vector")
