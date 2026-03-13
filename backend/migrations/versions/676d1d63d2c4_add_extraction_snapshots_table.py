"""add_extraction_snapshots_table

Revision ID: 676d1d63d2c4
Revises: 5ef8a8e61853
Create Date: 2026-03-13 23:45:00.000000

"""
# ruff: noqa: E501, I001
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '676d1d63d2c4'
down_revision: Union[str, Sequence[str], None] = '5ef8a8e61853'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'extraction_snapshots',
        sa.Column('id', sa.Uuid(), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('call_session_id', sa.Uuid(), nullable=False),
        sa.Column('schema_version', sa.String(length=64), nullable=False),
        sa.Column('prompt_version', sa.String(length=64), nullable=False),
        sa.Column('model_name', sa.String(length=128), nullable=False),
        sa.Column('extracted_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['call_session_id'], ['call_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_extraction_snapshots_call_session_id',
        'extraction_snapshots',
        ['call_session_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_extraction_snapshots_call_session_id',
        table_name='extraction_snapshots',
    )
    op.drop_table('extraction_snapshots')
