"""fix_embedding_dimension_3072

Revision ID: c96d49dcaa5b
Revises: 8713b8739826
Create Date: 2026-03-14 18:43:38.565244

"""

from typing import Sequence, Union

from alembic import op
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = 'c96d49dcaa5b'
down_revision: Union[str, Sequence[str], None] = '8713b8739826'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'memory_documents',
        'embedding',
        existing_type=Vector(768),
        type_=Vector(3072),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'memory_documents',
        'embedding',
        existing_type=Vector(3072),
        type_=Vector(768),
        existing_nullable=True,
    )
