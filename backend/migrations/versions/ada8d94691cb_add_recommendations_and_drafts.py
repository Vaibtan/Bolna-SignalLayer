"""add_recommendations_and_drafts

Revision ID: ada8d94691cb
Revises: 2c30964a416a
Create Date: 2026-03-14 14:53:26.867199

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "ada8d94691cb"
down_revision: Union[str, Sequence[str], None] = "2c30964a416a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "action_recommendations",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("call_session_id", sa.Uuid(), nullable=True),
        sa.Column(
            "target_stakeholder_id",
            sa.Uuid(),
            nullable=True,
        ),
        sa.Column(
            "action_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'proposed'"),
            nullable=False,
        ),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            (
                "status IN "
                "('proposed', 'accepted', 'dismissed', "
                "'edited', 'expired')"
            ),
            name="ck_action_recommendations_status",
        ),
        sa.ForeignKeyConstraint(
            ["call_session_id"],
            ["call_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_stakeholder_id"],
            ["stakeholders.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_action_recommendations_deal_id",
        "action_recommendations",
        ["deal_id"],
        unique=False,
    )
    op.create_table(
        "followup_drafts",
        sa.Column(
            "id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("call_session_id", sa.Uuid(), nullable=False),
        sa.Column(
            "draft_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default=sa.text("'draft'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["call_session_id"],
            ["call_sessions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["deal_id"],
            ["deals.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_followup_drafts_deal_id",
        "followup_drafts",
        ["deal_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_followup_drafts_deal_id",
        table_name="followup_drafts",
    )
    op.drop_table("followup_drafts")
    op.drop_index(
        "ix_action_recommendations_deal_id",
        table_name="action_recommendations",
    )
    op.drop_table("action_recommendations")
