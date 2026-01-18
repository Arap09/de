from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User
from app.models.platform_invitation import PlatformInvitation
from app.models.platform_membership import PlatformMembership
from app.models.salesperson_profile import SalespersonProfile

PLATFORM_INVITE_EXPIRY_DAYS = 7
INVITEE_TYPES = {"platform_admin", "salesperson"}
PLATFORM_ROLES = {"super_admin", "platform_admin"}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def generate_token() -> str:
    return secrets.token_urlsafe(48)


def generate_referral_code() -> str:
    # short, human-friendly-ish code; ensure uniqueness at insert with retry
    return secrets.token_urlsafe(9).replace("-", "").replace("_", "")[:12].upper()


async def ensure_no_pending_platform_invite(db: AsyncSession, *, email: str, invitee_type: str) -> None:
    now = _utcnow()
    stmt = (
        select(PlatformInvitation)
        .where(PlatformInvitation.email == normalize_email(email))
        .where(PlatformInvitation.invitee_type == invitee_type)
        .where(PlatformInvitation.accepted_at.is_(None))
        .where(PlatformInvitation.revoked_at.is_(None))
        .where(PlatformInvitation.expires_at > now)
    )
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Pending platform invitation already exists for this email/type")


async def create_platform_invitation(
    db: AsyncSession,
    *,
    inviter: User,
    email: str,
    invitee_type: str,
    platform_role: Optional[str] = None,
) -> PlatformInvitation:
    invitee_type = invitee_type.strip().lower()
    if invitee_type not in INVITEE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid invitee_type")

    if invitee_type == "platform_admin":
        if not platform_role:
            raise HTTPException(status_code=400, detail="platform_role is required for platform_admin invitations")
        pr = platform_role.strip().lower()
        if pr not in PLATFORM_ROLES:
            raise HTTPException(status_code=400, detail="Invalid platform_role")
        platform_role = pr
    else:
        platform_role = None

    email_n = normalize_email(email)
    await ensure_no_pending_platform_invite(db, email=email_n, invitee_type=invitee_type)

    inv = PlatformInvitation(
        inviter_user_id=inviter.id,
        email=email_n,
        invitee_type=invitee_type,
        platform_role=platform_role,
        token=generate_token(),
        expires_at=_utcnow() + timedelta(days=PLATFORM_INVITE_EXPIRY_DAYS),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return inv


async def accept_platform_invitation(
    db: AsyncSession,
    *,
    token: str,
    current_user: User,
) -> dict:
    token = token.strip()
    stmt = select(PlatformInvitation).where(PlatformInvitation.token == token)
    res = await db.execute(stmt)
    inv = res.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=404, detail="Platform invitation not found")
    if inv.revoked_at:
        raise HTTPException(status_code=400, detail="Platform invitation has been revoked")
    if inv.accepted_at:
        raise HTTPException(status_code=400, detail="Platform invitation already accepted")
    if inv.expires_at <= _utcnow():
        raise HTTPException(status_code=400, detail="Platform invitation has expired")

    if normalize_email(current_user.email) != inv.email:
        raise HTTPException(status_code=403, detail="Invitation email does not match authenticated user")

    # Mark accepted
    inv.accepted_at = _utcnow()

    result = {
        "invitee_type": inv.invitee_type,
        "platform_role": inv.platform_role,
        "platform_membership_created": False,
        "salesperson_profile_created": False,
        "referral_code": None,
    }

    if inv.invitee_type == "platform_admin":
        # Upsert platform membership
        stmt_pm = select(PlatformMembership).where(PlatformMembership.user_id == current_user.id)
        pm_res = await db.execute(stmt_pm)
        pm = pm_res.scalar_one_or_none()
        if pm:
            pm.role = inv.platform_role  # update role
            pm.is_active = True
        else:
            pm = PlatformMembership(
                user_id=current_user.id,
                role=inv.platform_role,
                is_active=True,
                created_by=inv.inviter_user_id,
            )
            db.add(pm)
            result["platform_membership_created"] = True

    elif inv.invitee_type == "salesperson":
        # Create salesperson profile if missing
        stmt_sp = select(SalespersonProfile).where(SalespersonProfile.user_id == current_user.id)
        sp_res = await db.execute(stmt_sp)
        sp = sp_res.scalar_one_or_none()
        if not sp:
            # generate unique code with retry on collision
            for _ in range(5):
                code = generate_referral_code()
                sp = SalespersonProfile(
                    user_id=current_user.id,
                    referral_code=code,
                    commission_amount_kes=getattr(settings, "DEFAULT_REFERRAL_REWARD_KES", 500),
                    is_active=True,
                    created_by=inv.inviter_user_id,
                )
                db.add(sp)
                try:
                    await db.commit()
                    await db.refresh(sp)
                    result["salesperson_profile_created"] = True
                    result["referral_code"] = sp.referral_code
                    break
                except Exception:
                    await db.rollback()
                    sp = None
            if not sp:
                raise HTTPException(status_code=500, detail="Could not generate unique referral code")
        else:
            result["referral_code"] = sp.referral_code

    await db.commit()
    await db.refresh(inv)
    return result
