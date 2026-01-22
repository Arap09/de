# app/services/invitations.py
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.tenant_invitation import TenantInvitation
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.models.tenant import Tenant
from app.services.email import email_service
from app.services.invitation_emails import build_invitation_email


# --------------------------------------------------
# Canonical tenant staff roles (no fancy titles)
# --------------------------------------------------
ALLOWED_INVITE_ROLES = {"ADMIN", "STAFF"}
INVITE_EXPIRY_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_invite_token() -> str:
    return secrets.token_urlsafe(48)


# --------------------------------------------------
# Tier staff limits (tenant STAFF only)
# - Pending invitations count toward limit
# - OWNER not counted
# - ADMIN and STAFF both consume seats
# --------------------------------------------------
def _tier_staff_limit(tenant: Tenant) -> int:
    """
    Uses tenant.tier to determine staff seat limit.
    - Sungura: 3
    - Swara: 6
    - Ndovu: 10+ (configurable)

    This is intentionally defensive because your Tenant.tier type may be str/enum.
    """
    tier = getattr(tenant, "tier", None)
    tier_s = str(tier).strip().upper() if tier is not None else ""

    if "SUNGURA" in tier_s:
        return 3
    if "SWARA" in tier_s:
        return 6
    if "NDOVU" in tier_s:
        # configurable; default 10
        return int(getattr(settings, "NDOVU_STAFF_LIMIT", 10))

    # Fallback (safe default)
    return int(getattr(settings, "DEFAULT_STAFF_LIMIT", 3))


async def _count_active_staff_members(db: AsyncSession, *, tenant_id) -> int:
    stmt = (
        select(func.count())
        .select_from(TenantMembership)
        .where(TenantMembership.tenant_id == tenant_id)
        .where(TenantMembership.is_active.is_(True))
        .where(TenantMembership.role.in_(["ADMIN", "STAFF"]))
    )
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


async def _count_pending_staff_invites(db: AsyncSession, *, tenant_id) -> int:
    now = _utcnow()
    stmt = (
        select(func.count())
        .select_from(TenantInvitation)
        .where(TenantInvitation.tenant_id == tenant_id)
        .where(TenantInvitation.accepted_at.is_(None))
        .where(TenantInvitation.revoked_at.is_(None))
        .where(TenantInvitation.expires_at > now)
        .where(TenantInvitation.role.in_(["ADMIN", "STAFF"]))
    )
    res = await db.execute(stmt)
    return int(res.scalar_one() or 0)


async def enforce_staff_limit_or_raise(db: AsyncSession, *, tenant: Tenant) -> None:
    """
    Applies only to tenant STAFF invitations.
    Pending invitations count toward the limit.
    """
    limit_ = _tier_staff_limit(tenant)
    active = await _count_active_staff_members(db, tenant_id=tenant.id)
    pending = await _count_pending_staff_invites(db, tenant_id=tenant.id)

    if (active + pending) >= limit_:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Staff limit reached for tenant tier (limit={limit_}). Active={active}, PendingInvites={pending}.",
        )


async def ensure_user_not_already_member(
    db: AsyncSession, *, tenant_id, email: str
) -> None:
    email_n = normalize_email(email)

    stmt_user = select(User).where(User.email == email_n)
    user_res = await db.execute(stmt_user)
    user = user_res.scalar_one_or_none()
    if not user:
        return

    stmt_mem = (
        select(TenantMembership)
        .where(TenantMembership.tenant_id == tenant_id)
        .where(TenantMembership.user_id == user.id)
    )
    mem_res = await db.execute(stmt_mem)
    existing = mem_res.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has membership in this tenant",
        )


async def ensure_no_pending_invite(
    db: AsyncSession, *, tenant_id, email: str, role: str
) -> None:
    email_n = normalize_email(email)
    now = _utcnow()

    stmt = (
        select(TenantInvitation)
        .where(TenantInvitation.tenant_id == tenant_id)
        .where(TenantInvitation.email == email_n)
        .where(TenantInvitation.role == role)
        .where(TenantInvitation.accepted_at.is_(None))
        .where(TenantInvitation.revoked_at.is_(None))
        .where(TenantInvitation.expires_at > now)
    )
    res = await db.execute(stmt)
    pending = res.scalar_one_or_none()
    if pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pending invitation already exists for this email and role",
        )


async def create_invitation(
    db: AsyncSession,
    *,
    tenant: Tenant,
    inviter: User,
    email: str,
    role: str,
) -> TenantInvitation:
    """
    Create a new tenant STAFF invitation.

    Enforces:
    - canonical roles: ADMIN/STAFF only
    - seat limits (active + pending invites)
    - prevents inviting existing members
    - prevents duplicate pending invites
    """
    role = role.strip().upper()
    if role not in ALLOWED_INVITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed: {', '.join(sorted(ALLOWED_INVITE_ROLES))}",
        )

    email_n = normalize_email(email)

    await enforce_staff_limit_or_raise(db, tenant=tenant)
    await ensure_user_not_already_member(db, tenant_id=tenant.id, email=email_n)
    await ensure_no_pending_invite(db, tenant_id=tenant.id, email=email_n, role=role)

    invitation = TenantInvitation(
        tenant_id=tenant.id,
        inviter_user_id=inviter.id,
        email=email_n,
        role=role,
        token=generate_invite_token(),
        expires_at=_utcnow() + timedelta(days=INVITE_EXPIRY_DAYS),
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    inviter_display_name = inviter.email  # until profile names exist
    accept_url = f"{settings.APP_BASE_URL.rstrip('/')}/accept-invitation?token={invitation.token}"

    msg = build_invitation_email(
        to_email=invitation.email,
        inviter_name=inviter_display_name,
        tenant_name=tenant.name,
        accept_url=accept_url,
    )
    await email_service.send(msg)

    return invitation


async def list_invitations(
    db: AsyncSession,
    *,
    tenant_id,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> List[TenantInvitation]:
    now = _utcnow()
    stmt = select(TenantInvitation).where(TenantInvitation.tenant_id == tenant_id)

    if status_filter:
        sf = status_filter.strip().lower()
        if sf == "pending":
            stmt = stmt.where(
                and_(
                    TenantInvitation.accepted_at.is_(None),
                    TenantInvitation.revoked_at.is_(None),
                    TenantInvitation.expires_at > now,
                )
            )
        elif sf == "accepted":
            stmt = stmt.where(TenantInvitation.accepted_at.is_not(None))
        elif sf == "revoked":
            stmt = stmt.where(TenantInvitation.revoked_at.is_not(None))
        elif sf == "expired":
            stmt = stmt.where(
                and_(
                    TenantInvitation.accepted_at.is_(None),
                    TenantInvitation.revoked_at.is_(None),
                    TenantInvitation.expires_at <= now,
                )
            )
        elif sf == "all":
            pass
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status filter. Use: pending|accepted|revoked|expired|all",
            )

    stmt = stmt.order_by(TenantInvitation.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def revoke_invitation(
    db: AsyncSession,
    *,
    tenant_id,
    invitation_id,
) -> TenantInvitation:
    stmt = (
        select(TenantInvitation)
        .where(TenantInvitation.id == invitation_id)
        .where(TenantInvitation.tenant_id == tenant_id)
    )
    res = await db.execute(stmt)
    invitation = res.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.accepted_at:
        raise HTTPException(status_code=400, detail="Cannot revoke an accepted invitation")

    if invitation.revoked_at:
        return invitation  # idempotent

    invitation.revoked_at = _utcnow()
    await db.commit()
    await db.refresh(invitation)
    return invitation


async def accept_invitation(
    db: AsyncSession,
    *,
    token: str,
    current_user: User,
) -> TenantMembership:
    token = token.strip()

    stmt = select(TenantInvitation).where(TenantInvitation.token == token)
    res = await db.execute(stmt)
    invitation = res.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.revoked_at:
        raise HTTPException(status_code=400, detail="Invitation has been revoked")

    if invitation.accepted_at:
        raise HTTPException(status_code=400, detail="Invitation already accepted")

    if invitation.expires_at <= _utcnow():
        raise HTTPException(status_code=400, detail="Invitation has expired")

    if normalize_email(current_user.email) != invitation.email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invitation email does not match authenticated user",
        )

    stmt_mem = (
        select(TenantMembership)
        .where(TenantMembership.tenant_id == invitation.tenant_id)
        .where(TenantMembership.user_id == current_user.id)
    )
    mem_res = await db.execute(stmt_mem)
    existing = mem_res.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Membership already exists")

    membership = TenantMembership(
        tenant_id=invitation.tenant_id,
        user_id=current_user.id,
        role=invitation.role,
        is_active=True,
    )

    db.add(membership)
    invitation.accepted_at = _utcnow()

    await db.commit()
    await db.refresh(membership)

    return membership
