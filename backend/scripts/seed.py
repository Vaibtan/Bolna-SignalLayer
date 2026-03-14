"""Seed script for the demo organization, user, deal, and stakeholders.

Run: cd backend && uv run python -m scripts.seed
"""

import asyncio

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import get_session_factory
from app.models.deal import Deal
from app.models.org import Organization
from app.models.stakeholder import Stakeholder
from app.models.user import User

ADMIN_EMAIL = "admin@signallayer.dev"
ADMIN_PASSWORD = "changeme123"
ORG_NAME = "Signal Layer OS Demo Org"
DEMO_DEAL_NAME = "Acme Corp Enterprise License"
SEED_LOCK_KEY = 662311903914221


async def seed() -> None:
    """Create the demo org, admin user, deal, and stakeholders."""
    factory = get_session_factory()
    async with factory() as session:
        session: AsyncSession

        await session.execute(
            text(f'SELECT pg_advisory_xact_lock({SEED_LOCK_KEY})')
        )

        # --- Organization ---
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

        # --- Admin user ---
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
        admin_user_id = user_result.scalar_one_or_none()
        if admin_user_id is None:
            existing_user = await session.execute(
                select(User.id).where(User.email == ADMIN_EMAIL)
            )
            admin_user_id = existing_user.scalar_one()

        # --- Demo deal ---
        deal_exists = await session.execute(
            select(Deal.id).where(
                Deal.org_id == org_id, Deal.name == DEMO_DEAL_NAME
            )
        )
        deal_id = deal_exists.scalar_one_or_none()

        if deal_id is None:
            deal = Deal(
                org_id=org_id,
                name=DEMO_DEAL_NAME,
                account_name="Acme Corp",
                stage="discovery",
                owner_user_id=admin_user_id,
            )
            session.add(deal)
            await session.flush()
            deal_id = deal.id

            # --- Demo stakeholders ---
            stakeholders = [
                Stakeholder(
                    deal_id=deal_id,
                    name="Jane Chen",
                    title="VP of Engineering",
                    department="Engineering",
                    email="jane.chen@acme.example",
                    phone="+1-555-0101",
                    source_type="manual",
                ),
                Stakeholder(
                    deal_id=deal_id,
                    name="Marcus Rivera",
                    title="Head of Procurement",
                    department="Procurement",
                    email="m.rivera@acme.example",
                    phone="+1-555-0102",
                    source_type="manual",
                ),
                Stakeholder(
                    deal_id=deal_id,
                    name="Priya Sharma",
                    title="CTO",
                    department="Executive",
                    email="priya.sharma@acme.example",
                    source_type="manual",
                ),
            ]
            for sh in stakeholders:
                session.add(sh)

            await session.commit()
            print(
                f"Seeded org '{ORG_NAME}', admin user, "
                f"deal '{DEMO_DEAL_NAME}', and "
                f'{len(stakeholders)} stakeholders.'
            )
        else:
            await session.commit()
            print(
                f"Org and admin exist. Deal '{DEMO_DEAL_NAME}' already seeded."
            )


if __name__ == "__main__":
    asyncio.run(seed())
