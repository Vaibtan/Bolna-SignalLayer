"""add_organization_name_unique_constraint

Revision ID: 1a9f7f7e5d8b
Revises: 4b3b686a1075
Create Date: 2026-03-13 20:10:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1a9f7f7e5d8b"
down_revision: Union[str, Sequence[str], None] = "4b3b686a1075"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_organizations_name",
        "organizations",
        ["name"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_organizations_name",
        "organizations",
        type_="unique",
    )
