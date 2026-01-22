# app/crud/user.py
from datetime import datetime, timedelta
from typing import Optional
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, TierEnum
from app.models.user_consent import UserConsent
from app.schemas.user import UserCreate
from app.core.config import settings


# -----------------------------------
# Queries
# -----------------------------------

async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    result = await db.execute(
        select(User).where(func.lower(User.email) == func.lower(email))
    )
    return result.scalar_one_or_none()


# -----------------------------------
# Consent helpers (tenant+role scoped, durable record)
# -----------------------------------

async def get_active_terms_consent(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    tenant_id: uuid.UUID,
    role: str,
    terms_version: str,
) -> Optional[UserConsent]:
    """
    Active consent = revoked_at IS NULL for the unique tuple.
    """
    result = await db.execute(
        select(UserConsent).where(
            and_(
                UserConsent.user_id == user_id,
                UserConsent.tenant_id == tenant_id,
                UserConsent.role == role,
                UserConsent.terms_version == terms_version,
                UserConsent.revoked_at.is_(None),
            )
        )
    )
    return result.scalar_one_or_none()


async def grant_terms_consent(
    db: AsyncSession,
    *,
    user: User,
    tenant_id: uuid.UUID,
    role: str,
    terms_version: str,
) -> UserConsent:
    """
    Idempotent grant: if already active, return it; else create one.
    """
    existing = await get_active_terms_consent(
        db,
        user_id=user.id,
        tenant_id=tenant_id,
        role=role,
        terms_version=terms_version,
    )
    if existing:
        return existing

    consent = UserConsent(
        user_id=user.id,
        tenant_id=tenant_id,
        role=role,
        terms_version=terms_version,
        revoked_at=None,
    )
    db.add(consent)
    await db.flush()
    await db.refresh(consent)
    return consent


# -----------------------------------
# Create user (magic-code signup)
# -----------------------------------

async def create_user(
    db: AsyncSession,
    payload: UserCreate,
    *,
    referred_by_id: Optional[uuid.UUID] = None,
    # IMPORTANT: since UserConsent.tenant_id is required, caller must pass it.
    tenant_id: Optional[uuid.UUID] = None,
    # for legal traceability (e.g., "client_owner_v1", "staff_v1", "salesperson_v1")
    role_for_terms: Optional[str] = None,
    terms_version: Optional[str] = None,
) -> User:
    now = datetime.utcnow()

    # If you require terms acceptance at signup, enforce it here:
    if payload.accepted_terms is not True:
        raise ValueError("accepted_terms must be True")

    user = User(
        email=payload.email.lower(),
        tier=payload.tier,
        referral_code=None,
        referred_by_id=referred_by_id,

        accepts_notifications=bool(payload.accepts_notifications),
        accepted_terms=True,
        terms_accepted_at=now,
        notifications_updated_at=(now if payload.accepts_notifications else None),

        trial_starts_at=now,
        trial_expires_at=now + timedelta(days=settings.TRIAL_PERIOD_DAYS),
        is_active=True,
        is_email_verified=False,
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Write durable consent record if all required params are present
    # (Because your table requires tenant_id, role, terms_version)
    if tenant_id and role_for_terms and terms_version:
        await grant_terms_consent(
            db,
            user=user,
            tenant_id=tenant_id,
            role=role_for_terms,
            terms_version=terms_version,
        )

    await db.refresh(user)
    return user


# -----------------------------------
# Mutations
# -----------------------------------

async def set_email_verified(db: AsyncSession, user: User) -> User:
    user.is_email_verified = True
    await db.flush()
    await db.refresh(user)
    return user


async def upgrade_tier(db: AsyncSession, user: User, new_tier: TierEnum) -> User:
    user.tier = new_tier
    await db.flush()
    await db.refresh(user)
    return user
