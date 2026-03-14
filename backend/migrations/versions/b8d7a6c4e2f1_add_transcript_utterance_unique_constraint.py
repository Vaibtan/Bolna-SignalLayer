"""add_transcript_utterance_unique_constraint

Revision ID: b8d7a6c4e2f1
Revises: a423fcbdf422
Create Date: 2026-03-14 12:10:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b8d7a6c4e2f1'
down_revision: Union[str, Sequence[str], None] = 'a423fcbdf422'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_transcript_utterances_call_session_sequence',
        'transcript_utterances',
        ['call_session_id', 'sequence_number'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'uq_transcript_utterances_call_session_sequence',
        'transcript_utterances',
        type_='unique',
    )
