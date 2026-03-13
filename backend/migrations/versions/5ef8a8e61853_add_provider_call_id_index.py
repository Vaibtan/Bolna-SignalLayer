"""add_provider_call_id_index

Revision ID: 5ef8a8e61853
Revises: 30770fd16af2
Create Date: 2026-03-13 19:57:35.264620

"""
# ruff: noqa: E501, I001
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5ef8a8e61853'
down_revision: Union[str, Sequence[str], None] = '30770fd16af2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_call_sessions_provider_call_id', 'call_sessions', ['provider_call_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_call_sessions_provider_call_id', table_name='call_sessions')
