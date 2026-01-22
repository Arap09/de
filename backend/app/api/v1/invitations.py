# app/api/v1/auth.py
from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    MagicCodeRequestStaff,
    MagicCodeRequestTenant,
    MagicCodeVerify,
    NotificationsPreferenceUpdate,
)
from app.services.auth import (
    request_magic_code,
    verify_magic_code,
    get_current_user,
)
from app.models.user import User

# TENANT / CONSENT
from app.api.deps import get_current_membership, require_consent
from app.models.tenant_membership import TenantMembership
from app.models.user_consent import UserConsent


router = APIRouter(prefix="/auth", tags=["Auth"])


# --------------------------------------------------
# Request magic code — STAFF entrypoint (email only)
# --------------------------------------------------
@router.post("/request-code/staff", status_code=status.HTTP_204_NO_CONTENT)
async def request_code_staff(
    payload: MagicCodeRequestStaff,
    db: AsyncSession = Depends(get_db),
):
    """
    For:
    - Tenant staff
    - Platform staff
    - Salespeople

    Email-only. No ToS here (ToS happens post-auth via consent).
    """
    await request_magic_code(db, payload)


# --------------------------------------------------
# Request magic code — TENANT OWNER entrypoint (enforced)
# --------------------------------------------------
@router.post("/request-code/tenant", status_code=status.HTTP_204_NO_CONTENT)
async def request_code_tenant(
    payload: MagicCodeRequestTenant,
    db: AsyncSession = Depends(get_db),
):
    """
    Tenant OWNER signup/login entrypoint.

    Requires:
    - email
    - tier (chosen on homepage)
    - accepted_terms == True
    - accepts_notifications optional (default False)
    - referral_code optional
    """
    if payload.accepted_terms is not True:
        raise HTTPException(status_code=400, detail="You must accept Terms of Service to continue.")

    # tier is required by schema; keep defensive check anyway
    if not payload.tier:
        raise HTTPException(status_code=400, detail="Tier is required.")

    await request_magic_code(db, payload)


# --------------------------------------------------
# Verify magic code (shared)
# --------------------------------------------------
@router.post("/verify-code")
async def verify_code(
    payload: MagicCodeVerify,
    db: AsyncSession = Depends(get_db),
):
    """
    Shared verification for all identities.
    """
    result = await verify_magic_code(
        db,
        email=payload.email,
        code=payload.code,
    )

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
        "tenant_id": result.get("tenant_id"),
    }


# --------------------------------------------------
# Current authenticated user (tenant-aware)
# --------------------------------------------------
@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
    _: bool = Depends(require_consent),
):
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "accepts_notifications": getattr(current_user, "accepts_notifications", False),
        },
        "tenant": {"id": membership.tenant_id},
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
    Accept role-specific ToS (post-auth).
    Notifications is separate and global.
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


# --------------------------------------------------
# Global notifications preference (POST-AUTH, any user)
# --------------------------------------------------
@router.post("/notifications", status_code=status.HTTP_204_NO_CONTENT)
async def set_notifications_preference(
    payload: NotificationsPreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Global opt-in/out. Applies to:
    - tenant owners
    - tenant staff
    - platform staff
    - salespeople
    """
    current_user.accepts_notifications = payload.accepts_notifications
    db.add(current_user)
    await db.commit()
