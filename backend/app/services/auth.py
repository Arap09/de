import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select

from app.schemas.user import MagicCodeRequest, UserCreate
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


# --------------------------------------------------
# Helper: Purge all expired magic codes globally
# --------------------------------------------------
async def purge_expired_magic_codes(db: AsyncSession) -> None:
    """
    Remove all expired magic codes from the database.
    """
    stmt = (
        update(User)
        .where(User.magic_code_expires_at < datetime.now(timezone.utc))
        .values(magic_code=None, magic_code_expires_at=None)
    )
    await db.execute(stmt)
    await db.commit()


# --------------------------------------------------
# Request magic code
# --------------------------------------------------
async def request_magic_code(
    db: AsyncSession,
    payload: MagicCodeRequest,
) -> None:
    """
    Generate a new magic code for the given email.
    """
    await purge_expired_magic_codes(db)

    user = await get_user_by_email(db, payload.email)

    if not user:
        user_payload = UserCreate(
            email=payload.email,
            tier=payload.tier,
            referral_code=payload.referral_code,
            accepts_notifications=payload.accepts_notifications,
            accepted_terms=payload.accepted_terms,
        )
        user = await create_user(db=db, payload=user_payload)
    else:
        if (
            user.magic_code_expires_at
            and user.magic_code_expires_at < datetime.now(timezone.utc)
        ):
            user.magic_code = None
            user.magic_code_expires_at = None
            await db.commit()

    code = f"{secrets.randbelow(1_000_000):06d}"
    user.magic_code = code
    user.magic_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=MAGIC_CODE_EXPIRY_MINUTES
    )

    await db.commit()


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
    - Creates tenant + OWNER role on first login
    - Resolves the active tenant
    - Embeds tenant_id into JWT
    """
    user = await get_user_by_email(db, email)

    if not user or user.magic_code != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid magic code",
        )

    if (
        not user.magic_code_expires_at
        or user.magic_code_expires_at < datetime.now(timezone.utc)
    ):
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

    # --------------------------------------------------
    # Resolve or bootstrap tenant membership
    # --------------------------------------------------
    stmt = select(TenantMembership).where(
        TenantMembership.user_id == user.id
    )
    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    # First login → create tenant + OWNER role
    if not membership:
        tenant = Tenant(
            name=f"{user.email.split('@')[0]}'s Workspace",
            created_by=user.id,
        )
        db.add(tenant)
        await db.flush()  # get tenant.id

        membership = TenantMembership(
            user_id=user.id,
            tenant_id=tenant.id,
            role=TenantRole.OWNER,
            created_by=user.id,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(membership)

    # --------------------------------------------------
    # ISSUE TENANT-AWARE ACCESS TOKEN (CRITICAL FIX)
    # --------------------------------------------------
    access_token = create_access_token(
        subject=user.email,
        extra_claims={
            "tenant_id": str(membership.tenant_id),
        },
    )

    return {
        "access_token": access_token,
        "tenant_id": membership.tenant_id,
    }


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
        email: str | None = payload.get("sub")

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

    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
