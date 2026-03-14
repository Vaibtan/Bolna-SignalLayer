"""add_memory_documents_table

Revision ID: 8713b8739826
Revises: 65f7e76db46c
Create Date: 2026-03-14 15:48:42.505739

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8713b8739826'
down_revision: Union[str, Sequence[str], None] = '65f7e76db46c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'memory_documents',
        sa.Column(
            'id',
            sa.Uuid(),
            server_default=sa.text('gen_random_uuid()'),
            nullable=False,
        ),
        sa.Column('deal_id', sa.Uuid(), nullable=False),
        sa.Column(
            'stakeholder_id', sa.Uuid(), nullable=True,
        ),
        sa.Column(
            'call_session_id', sa.Uuid(), nullable=True,
        ),
        sa.Column(
            'doc_type',
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column(
            'metadata_json',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['call_session_id'],
            ['call_sessions.id'],
            ondelete='SET NULL',
        ),
        sa.ForeignKeyConstraint(
            ['deal_id'],
            ['deals.id'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['stakeholder_id'],
            ['stakeholders.id'],
            ondelete='SET NULL',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_memory_documents_deal_id',
        'memory_documents',
        ['deal_id'],
        unique=False,
    )
    op.create_index(
        'ix_memory_documents_doc_type',
        'memory_documents',
        ['doc_type'],
        unique=False,
    )
    op.create_index(
        'ix_memory_documents_stakeholder_id',
        'memory_documents',
        ['stakeholder_id'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        'ix_memory_documents_stakeholder_id',
        table_name='memory_documents',
    )
    op.drop_index(
        'ix_memory_documents_doc_type',
        table_name='memory_documents',
    )
    op.drop_index(
        'ix_memory_documents_deal_id',
        table_name='memory_documents',
    )
    op.drop_table('memory_documents')
