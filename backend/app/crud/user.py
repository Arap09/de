from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, TierEnum
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.config import settings


# -----------------------------------
# Queries
# -----------------------------------

async def get_user_by_id(
    db: AsyncSession,
    user_id: int
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(
    db: AsyncSession,
    email: str
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_user_by_phone(
    db: AsyncSession,
    phone_number: str
) -> Optional[User]:
    result = await db.execute(
        select(User).where(User.phone_number == phone_number)
    )
    return result.scalar_one_or_none()


# -----------------------------------
# Create user
# -----------------------------------

async def create_user(
    db: AsyncSession,
    payload: UserCreate,
    *,
    hashed_password: str,
    referral_code: Optional[str] = None,
    referred_by_id: Optional[int] = None,
) -> User:
    now = datetime.utcnow()

    user = User(
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        country_code=payload.country_code,
        phone_number=payload.phone_number,
        hashed_password=hashed_password,
        tier=payload.tier or TierEnum.sungura,
        referral_code=referral_code,
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
    user: User
) -> User:
    user.is_email_verified = True
    await db.commit()
    await db.refresh(user)
    return user


async def set_password(
    db: AsyncSession,
    user: User,
    new_password: str
) -> User:
    user.hashed_password = hash_password(new_password)
    await db.commit()
    await db.refresh(user)
    return user


async def upgrade_tier(
    db: AsyncSession,
    user: User,
    new_tier: TierEnum
) -> User:
    user.tier = new_tier
    await db.commit()
    await db.refresh(user)
    return user
