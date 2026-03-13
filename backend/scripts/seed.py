"""Seed script — creates a demo organization and admin user.

Run: cd backend && uv run python -m scripts.seed
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.org import Organization
from app.models.user import User

ADMIN_EMAIL = "admin@dealgraph.dev"
ADMIN_PASSWORD = "changeme123"
ORG_NAME = "DealGraph Demo Org"


async def seed() -> None:
    """Create the demo org and admin user without duplicate seed artifacts."""
    factory = get_session_factory()
    async with factory() as session:
        session: AsyncSession

        org_insert = (
            pg_insert(Organization)
            .values(name=ORG_NAME)
            .on_conflict_do_nothing(index_elements=["name"])
            .returning(Organization.id)
        )
        org_result = await session.execute(org_insert)
        org_id = org_result.scalar_one_or_none()
        if org_id is None:
            existing_org = await session.execute(
                select(Organization.id).where(Organization.name == ORG_NAME)
            )
            org_id = existing_org.scalar_one()

        user_insert = (
            pg_insert(User)
            .values(
                org_id=org_id,
                name="Admin",
                email=ADMIN_EMAIL,
                password_hash=hash_password(ADMIN_PASSWORD),
                role="admin",
            )
            .on_conflict_do_nothing(index_elements=["email"])
            .returning(User.id)
        )
        user_result = await session.execute(user_insert)
        user_id = user_result.scalar_one_or_none()

        if user_id is None:
            await session.rollback()
            print(f"Admin user {ADMIN_EMAIL} already exists — skipping.")
            return

        await session.commit()
        print(f"Seeded org '{ORG_NAME}' and admin user '{ADMIN_EMAIL}'.")


if __name__ == "__main__":
    asyncio.run(seed())
