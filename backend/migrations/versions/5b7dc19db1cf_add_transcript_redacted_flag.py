"""add_transcript_redacted_flag

Revision ID: 5b7dc19db1cf
Revises: 00d8f6cf3d3a
Create Date: 2026-03-14 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5b7dc19db1cf"
down_revision: Union[str, Sequence[str], None] = "00d8f6cf3d3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "call_sessions",
        sa.Column(
            "transcript_redacted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("call_sessions", "transcript_redacted")
