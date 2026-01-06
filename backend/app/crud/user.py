from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, TierEnum
from app.schemas.user import UserCreate
from app.core.config import settings


# -----------------------------------
# Queries
# -----------------------------------

async def get_user_by_id(
    db: AsyncSession,
    user_id: int,
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str,
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


# -----------------------------------
# Create user (magic-code signup)
# -----------------------------------

async def create_user(
    db: AsyncSession,
    payload: UserCreate,
    *,
    referred_by_id: Optional[int] = None,
) -> User:
    now = datetime.utcnow()

    user = User(
        email=payload.email,
        tier=payload.tier,
        referral_code=payload.referral_code,
        referred_by_id=referred_by_id,
        accepts_notifications=payload.accepts_notifications,
        accepted_terms=payload.accepted_terms,
        trial_starts_at=now,
        trial_expires_at=now + timedelta(days=settings.TRIAL_PERIOD_DAYS),
        is_active=True,
        is_email_verified=False,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# -----------------------------------
# Mutations
# -----------------------------------

async def set_email_verified(
    db: AsyncSession,
    user: User,
) -> User:
    user.is_email_verified = True
    await db.commit()
    await db.refresh(user)
    return user


async def upgrade_tier(
    db: AsyncSession,
    user: User,
    new_tier: TierEnum,
) -> User:
    user.tier = new_tier
    await db.commit()
    await db.refresh(user)
    return user
