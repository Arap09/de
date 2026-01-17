from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_invitation import TenantInvitation
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.models.tenant import Tenant


ALLOWED_INVITE_ROLES = {"ADMIN", "MANAGER", "AGENT", "SALES"}
INVITE_EXPIRY_DAYS = 7


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_invite_token() -> str:
    # token_urlsafe(48) -> ~64 chars, high entropy
    return secrets.token_urlsafe(48)


async def ensure_user_not_already_member(
    db: AsyncSession, *, tenant_id, email: str
) -> None:
    """
    Prevent inviting someone who already has a membership in this tenant.
    """
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
    """
    Prevent duplicate pending invitations.
    """
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
    Create a new invitation.

    NOTE:
    - Tier-based agent limits can be enforced here later (Phase 3/4).
    - Email send is intentionally stubbed (you can integrate your mailer).
    """
    role = role.strip().upper()
    if role not in ALLOWED_INVITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Allowed: {', '.join(sorted(ALLOWED_INVITE_ROLES))}",
        )

    email_n = normalize_email(email)

    # Hard block inviting OWNER via this flow
    if role == "OWNER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot invite OWNER via invitations endpoint",
        )

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

    # TODO: integrate email sending (e.g., app/services/mailer.py)
    # await send_invitation_email(invitation, tenant_name=tenant.name, inviter_email=inviter.email)

    return invitation


async def list_invitations(
    db: AsyncSession,
    *,
    tenant_id,
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> List[TenantInvitation]:
    """
    List invitations for a tenant.

    status_filter: pending|accepted|revoked|expired|all
    """
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
    """
    Revoke a pending invitation (idempotent).
    """
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
    """
    Accept an invitation.

    This endpoint is intentionally NOT guarded by require_consent
    because consent is required AFTER membership is created.

    Flow:
    - Validate invitation token
    - Verify email matches authenticated user
    - Create tenant membership
    - Mark invitation accepted
    """
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

    # Prevent duplicates if user was already added by admin manually
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
