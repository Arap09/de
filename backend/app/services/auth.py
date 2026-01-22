# app/services/auth.py
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate
from app.crud.user import get_user_by_email, create_user
from app.core.security import (
    create_access_token,
    decode_access_token,
    bearer_scheme,
)
from app.db.session import get_db
from app.models.user import User

# Tenant / RBAC imports
from app.models.tenant import Tenant
from app.models.tenant_membership import TenantMembership
from app.core.roles import TenantRole

MAGIC_CODE_EXPIRY_MINUTES = 10


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------
# Helper: Purge all expired magic codes globally
# --------------------------------------------------
async def purge_expired_magic_codes(db: AsyncSession) -> None:
    """
    Remove all expired magic codes from the database.
    """
    stmt = (
        update(User)
        .where(User.magic_code_expires_at.is_not(None))
        .where(User.magic_code_expires_at < _utcnow())
        .values(magic_code=None, magic_code_expires_at=None)
    )
    await db.execute(stmt)
    await db.commit()


# --------------------------------------------------
# Helpers: payload-safe access (supports multiple request models)
# --------------------------------------------------
def _payload_get(payload: Any, name: str, default: Any = None) -> Any:
    return getattr(payload, name, default)


def _is_truthy(val: Any) -> bool:
    return val is True


# --------------------------------------------------
# Request magic code
# --------------------------------------------------
async def request_magic_code(
    db: AsyncSession,
    payload: Any,  # supports MagicCodeRequestStaff or MagicCodeRequestTenant (or legacy MagicCodeRequest)
) -> None:
    """
    Generate a new magic code for the given email.

    Canonical behavior:
    - STAFF/PLATFORM/SALES request-code: email only.
    - TENANT OWNER request-code: requires tier + accepted_terms.
    - Notifications is optional and global; persist only if provided.
    - Referral code is optional; persist only if provided.
    """
    await purge_expired_magic_codes(db)

    email: str = str(_payload_get(payload, "email")).strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    user = await get_user_by_email(db, email)

    # Detect whether this request is the TENANT OWNER entrypoint
    tier = _payload_get(payload, "tier", None)
    accepted_terms = _payload_get(payload, "accepted_terms", None)

    is_tenant_owner_entrypoint = (tier is not None) or (accepted_terms is not None)

    if not user:
        # If tenant owner entrypoint, enforce required fields
        if is_tenant_owner_entrypoint:
            if tier is None:
                raise HTTPException(status_code=400, detail="Tier is required for tenant signup")
            if not _is_truthy(accepted_terms):
                raise HTTPException(status_code=400, detail="You must accept Terms of Service to continue")

        # Notifications optional (global). Default False unless provided.
        accepts_notifications = bool(_payload_get(payload, "accepts_notifications", False))
        referral_code = _payload_get(payload, "referral_code", None)

        # If staff entrypoint, tier may be None. But your User model currently requires tier.
        # In POSTIKA, tenant OWNER creates the tenant; staff are invited and still must have a tier field on user.
        # Therefore: if tier not provided, assign a safe default *ONLY for user record creation*.
        # This does not bypass tenant-tier enforcement; tenant creation still uses tenant tier.
        if tier is None:
            # Keep backward compatibility with your existing schema which used TierEnum.sungura as default.
            # If you prefer a different default, change here.
            from app.schemas.user import TierEnum
            tier = TierEnum.sungura

        user_payload = UserCreate(
            email=email,
            tier=tier,
            referral_code=referral_code,
            accepts_notifications=accepts_notifications,
            accepted_terms=bool(accepted_terms) if accepted_terms is not None else False,
        )
        user = await create_user(db=db, payload=user_payload)

    else:
        # Existing user: clear expired codes if needed (idempotent)
        if user.magic_code_expires_at and user.magic_code_expires_at < _utcnow():
            user.magic_code = None
            user.magic_code_expires_at = None

        # If tenant owner entrypoint includes notifications preference, update it globally.
        # If not included, do not override existing preference.
        if hasattr(payload, "accepts_notifications"):
            user.accepts_notifications = bool(_payload_get(payload, "accepts_notifications", False))

        # If referral code supplied (rare for existing users), store if your model supports it.
        # Only set if provided and user.referral_code is empty.
        if hasattr(payload, "referral_code"):
            rc = _payload_get(payload, "referral_code", None)
            if rc and not getattr(user, "referral_code", None):
                user.referral_code = rc

        await db.commit()

    # Generate and store code
    code = f"{secrets.randbelow(1_000_000):06d}"
    user.magic_code = code
    user.magic_code_expires_at = _utcnow() + timedelta(minutes=MAGIC_CODE_EXPIRY_MINUTES)

    await db.commit()

    # NOTE: delivery is handled elsewhere (email service). This function only sets the code.


# --------------------------------------------------
# Verify magic code (ISSUES TENANT-AWARE JWT)
# --------------------------------------------------
async def verify_magic_code(
    db: AsyncSession,
    *,
    email: str,
    code: str,
) -> dict:
    """
    Verify a magic code and issue a TENANT-AWARE JWT.

    Behavior:
    - Verifies magic code
    - Clears magic code + marks email verified
    - If user has no membership yet, bootstraps tenant + OWNER membership
    - Issues JWT with tenant_id claim
    """
    email_n = email.strip().lower()
    user = await get_user_by_email(db, email_n)

    if not user or user.magic_code != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid magic code",
        )

    if (not user.magic_code_expires_at) or (user.magic_code_expires_at < _utcnow()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic code expired",
        )

    # Clear magic code + mark email verified
    user.is_email_verified = True
    user.magic_code = None
    user.magic_code_expires_at = None
    await db.commit()
    await db.refresh(user)

    # Resolve membership (if any)
    stmt = select(TenantMembership).where(TenantMembership.user_id == user.id)
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    # First login with no membership => bootstrap tenant + OWNER
    if not membership:
        tenant = Tenant(
            name=f"{user.email.split('@')[0]}'s Workspace",
            created_by=user.id,
        )
        db.add(tenant)
        await db.flush()  # obtains tenant.id

        membership = TenantMembership(
            user_id=user.id,
            tenant_id=tenant.id,
            role=TenantRole.OWNER.value,  # store as string: "owner"
            created_by=user.id,
            is_active=True if hasattr(TenantMembership, "is_active") else True,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)

    # Issue token with tenant claim
    access_token = create_access_token(
        subject=user.email,
        extra_claims={"tenant_id": str(membership.tenant_id)},
    )

    return {"access_token": access_token, "tenant_id": membership.tenant_id}


# --------------------------------------------------
# Get current authenticated user (IDENTITY ONLY)
# --------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the authenticated user from JWT.
    Tenant validation is intentionally NOT done here.
    """
    try:
        payload = decode_access_token(credentials.credentials)
        email: Optional[str] = payload.get("sub")
        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await get_user_by_email(db, email.strip().lower())
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
