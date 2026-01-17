from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import MagicCodeRequest, MagicCodeVerify
from app.services.auth import (
    request_magic_code,
    verify_magic_code,
    get_current_user,
)
from app.models.user import User

# TENANT / RBAC / CONSENT
from app.api.deps import (
    get_current_membership,
    require_consent,  # Consent gate (post-auth)
)
from app.models.tenant_membership import TenantMembership
from app.models.user_consent import UserConsent

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

# --------------------------------------------------
# Request magic code
# --------------------------------------------------
@router.post(
    "/request-code",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def request_code(
    payload: MagicCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Entry point for all identities.
    NO business logic.
    NO consent logic.
    """
    await request_magic_code(db, payload)


# --------------------------------------------------
# Verify magic code (login / first signup)
# --------------------------------------------------
@router.post("/verify-code")
async def verify_code(
    payload: MagicCodeVerify,
    db: AsyncSession = Depends(get_db),
):
    """
    This endpoint:
    - Verifies the magic code
    - Creates user if needed
    - Creates tenant if first login
    - Assigns OWNER role on tenant creation
    - Returns JWT access token

    IMPORTANT:
    - No consent checks here
    - Consent is enforced post-auth
    """

    result = await verify_magic_code(
        db,
        email=payload.email,
        code=payload.code,
    )

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "tenant_id": result["tenant_id"],
    }


# --------------------------------------------------
# Current authenticated user (TENANT + CONSENT AWARE)
# --------------------------------------------------
@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
    _: bool = Depends(require_consent),
):
    """
    Tenant-aware identity endpoint.

    Requires:
    - Authorization: Bearer <token>
    - X-Tenant-Id header
    - Role-specific consent acceptance
    """

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
        },
        "tenant": {
            "id": membership.tenant_id,
        },
        "role": membership.role,
    }


# --------------------------------------------------
# Accept role-specific consent (POST-AUTH)
# --------------------------------------------------
@router.post("/consent/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_consent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
):
    """
    Accept role-specific terms and conditions.

    DESIGN:
    - Post-auth only
    - Tenant-scoped
    - Role-scoped
    - Idempotent
    """

    stmt = (
        select(UserConsent)
        .where(UserConsent.user_id == current_user.id)
        .where(UserConsent.tenant_id == membership.tenant_id)
        .where(UserConsent.role == membership.role)
        .where(UserConsent.revoked_at.is_(None))
    )

    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return

    consent = UserConsent(
        user_id=current_user.id,
        tenant_id=membership.tenant_id,
        role=membership.role,
        accepted_at=datetime.utcnow(),
    )

    db.add(consent)
    await db.commit()


# --------------------------------------------------
# Check consent status (frontend bootstrap)
# --------------------------------------------------
@router.get("/consent/status")
async def consent_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
):
    stmt = (
        select(UserConsent)
        .where(UserConsent.user_id == current_user.id)
        .where(UserConsent.tenant_id == membership.tenant_id)
        .where(UserConsent.role == membership.role)
        .where(UserConsent.revoked_at.is_(None))
    )

    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()

    return {
        "role": membership.role,
        "consent_accepted": bool(consent),
    }
