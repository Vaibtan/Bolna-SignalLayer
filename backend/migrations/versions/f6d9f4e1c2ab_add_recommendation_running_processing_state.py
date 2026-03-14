"""add_recommendation_running_processing_state

Revision ID: f6d9f4e1c2ab
Revises: ada8d94691cb
Create Date: 2026-03-14 17:35:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6d9f4e1c2ab"
down_revision: Union[str, Sequence[str], None] = "ada8d94691cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_OLD_CHECK = (
    "processing_status IN "
    "('pending', 'transcript_partial', 'transcript_finalized', "
    "'extraction_running', 'extraction_completed', "
    "'snapshots_updating', 'risk_running', "
    "'recommendation_completed', 'failed_retryable', "
    "'failed_terminal')"
)

_NEW_CHECK = (
    "processing_status IN "
    "('pending', 'transcript_partial', 'transcript_finalized', "
    "'extraction_running', 'extraction_completed', "
    "'snapshots_updating', 'risk_running', "
    "'recommendation_running', 'recommendation_completed', "
    "'failed_retryable', 'failed_terminal')"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        "ck_call_sessions_processing_status",
        "call_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_call_sessions_processing_status",
        "call_sessions",
        _NEW_CHECK,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "ck_call_sessions_processing_status",
        "call_sessions",
        type_="check",
    )
    op.create_check_constraint(
        "ck_call_sessions_processing_status",
        "call_sessions",
        _OLD_CHECK,
    )
