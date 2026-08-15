"""Seed script — creates the initial superadmin user.

Usage:
    python -m scripts.seed   (run from the backend directory)
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import engine
from app.models.user import User, UserRole


async def seed(db: AsyncSession) -> None:
    """Create the superadmin if it does not already exist."""
    existing = await db.execute(select(User).where(User.email == settings.SEED_ADMIN_EMAIL))
    admin = existing.scalar_one_or_none()

    if admin:
        print(f"[seed] Superadmin {settings.SEED_ADMIN_EMAIL} already exists — skipping.")
        return

    hashed = bcrypt.hashpw(
        settings.SEED_ADMIN_PASSWORD.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    admin = User(
        email=settings.SEED_ADMIN_EMAIL,
        hashed_password=hashed,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin)
    await db.commit()
    await db.refresh(admin)

    print(f"[seed] Created superadmin — email: {admin.email}  password: {settings.SEED_ADMIN_PASSWORD}")


async def main() -> None:
    async with async_sessionmaker(engine, expire_on_commit=False)() as db:
        await seed(db)
    print("[seed] Done.")


if __name__ == "__main__":
    asyncio.run(main())