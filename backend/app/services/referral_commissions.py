from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.payout_batch import PayoutBatch
from app.models.referral_commission import ReferralCommission
from app.models.salesperson_profile import SalespersonProfile
from app.models.tenant import Tenant


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# -----------------------------
# Status transitions (single source of truth)
# -----------------------------
COMMISSION_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"approved", "rejected"},
    "approved": {"batched"},
    "batched": {"paid"},
    "rejected": set(),
    "paid": set(),
}


def _normalize_status(value: str) -> str:
    return (value or "").strip().lower()


def assert_commission_transition(from_status: str, to_status: str) -> None:
    f = _normalize_status(from_status)
    t = _normalize_status(to_status)
    allowed = COMMISSION_TRANSITIONS.get(f, set())
    if t not in allowed:
        raise ValueError(f"Invalid commission transition: {f} -> {t}")


async def require_active_salesperson_profile(db: AsyncSession, *, user_id: UUID) -> SalespersonProfile:
    stmt = select(SalespersonProfile).where(SalespersonProfile.user_id == user_id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile or not profile.is_active:
        raise LookupError("Salesperson access required")
    return profile


# -----------------------------
# Commission creation hook (unchanged behavior)
# -----------------------------
async def create_commission_for_subscription(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    billing_event: str,
    subscription_id: Optional[UUID] = None,
    amount_kes_override: Optional[int] = None,
) -> Optional[ReferralCommission]:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return None

    referral_code = tenant.referral_code_used
    if not referral_code:
        return None

    referral_code = referral_code.strip().upper()
    if not referral_code:
        return None

    stmt_sp = select(SalespersonProfile).where(
        SalespersonProfile.referral_code == referral_code,
        SalespersonProfile.is_active.is_(True),
    )
    sp_res = await db.execute(stmt_sp)
    salesperson = sp_res.scalar_one_or_none()
    if not salesperson:
        return None

    if subscription_id is not None:
        stmt_existing = select(ReferralCommission).where(
            and_(
                ReferralCommission.tenant_id == tenant_id,
                ReferralCommission.subscription_id == subscription_id,
                ReferralCommission.billing_event == billing_event,
            )
        )
        existing_res = await db.execute(stmt_existing)
        if existing_res.scalar_one_or_none():
            return None

    amount_kes = (
        int(amount_kes_override)
        if amount_kes_override is not None
        else int(salesperson.commission_amount_kes or getattr(settings, "DEFAULT_REFERRAL_REWARD_KES", 500))
    )

    commission = ReferralCommission(
        salesperson_user_id=salesperson.user_id,
        tenant_id=tenant_id,
        subscription_id=subscription_id,
        billing_event=billing_event,
        amount_kes=amount_kes,
        currency="KES",
        status="pending",
        source_referral_code=referral_code,
        created_at=_utcnow(),
    )

    db.add(commission)
    await db.commit()
    await db.refresh(commission)
    return commission


# -----------------------------
# Approval flow (platform admin / super admin for now)
# -----------------------------
async def approve_commission(
    db: AsyncSession,
    *,
    commission_id: UUID,
    notes: Optional[str] = None,
) -> ReferralCommission:
    commission = await db.get(ReferralCommission, commission_id)
    if not commission:
        raise LookupError("Commission not found")

    assert_commission_transition(commission.status, "approved")
    commission.status = "approved"
    if notes:
        commission.notes = notes

    await db.commit()
    await db.refresh(commission)
    return commission


async def reject_commission(
    db: AsyncSession,
    *,
    commission_id: UUID,
    reason: str,
) -> ReferralCommission:
    commission = await db.get(ReferralCommission, commission_id)
    if not commission:
        raise LookupError("Commission not found")

    assert_commission_transition(commission.status, "rejected")
    commission.status = "rejected"
    commission.notes = (reason or "").strip()[:500] or "Rejected"

    await db.commit()
    await db.refresh(commission)
    return commission


# -----------------------------
# Payout batching (salesperson self-service)
# -----------------------------
async def create_payout_batch_for_salesperson(
    db: AsyncSession,
    *,
    salesperson_user_id: UUID,
    currency: str = "KES",
    max_items: int = 500,
) -> PayoutBatch:
    # Ensure salesperson is active
    await require_active_salesperson_profile(db, user_id=salesperson_user_id)

    cur = (currency or "KES").strip().upper()

    # Lock eligible commissions to prevent double-batching under concurrency
    stmt = (
        select(ReferralCommission)
        .where(
            ReferralCommission.salesperson_user_id == salesperson_user_id,
            ReferralCommission.currency == cur,
            ReferralCommission.status == "approved",
            ReferralCommission.payout_batch_id.is_(None),
        )
        .order_by(ReferralCommission.created_at.asc())
        .limit(max_items)
        .with_for_update()
    )
    res = await db.execute(stmt)
    commissions: Sequence[ReferralCommission] = list(res.scalars().all())

    if not commissions:
        raise ValueError("No approved commissions available for batching")

    total = sum(int(c.amount_kes) for c in commissions)

    batch = PayoutBatch(
        salesperson_user_id=salesperson_user_id,
        currency=cur,
        status="draft",
        total_amount_kes=int(total),
        created_at=_utcnow(),
    )
    db.add(batch)
    await db.flush()  # assign batch.id without committing yet

    # Update commissions
    for c in commissions:
        assert_commission_transition(c.status, "batched")
        c.status = "batched"
        c.payout_batch_id = batch.id

    await db.commit()
    await db.refresh(batch)
    return batch


async def submit_payout_batch(
    db: AsyncSession,
    *,
    batch_id: UUID,
    salesperson_user_id: UUID,
) -> PayoutBatch:
    batch = await db.get(PayoutBatch, batch_id)
    if not batch:
        raise LookupError("Batch not found")

    if batch.salesperson_user_id != salesperson_user_id:
        raise PermissionError("Not allowed")

    if _normalize_status(batch.status) != "draft":
        raise ValueError("Only draft batches can be submitted")

    batch.status = "submitted"
    batch.submitted_at = _utcnow()

    await db.commit()
    await db.refresh(batch)
    return batch


async def mark_payout_batch_paid(
    db: AsyncSession,
    *,
    batch_id: UUID,
) -> PayoutBatch:
    batch = await db.get(PayoutBatch, batch_id)
    if not batch:
        raise LookupError("Batch not found")

    if _normalize_status(batch.status) != "submitted":
        raise ValueError("Only submitted batches can be marked paid")

    # Lock all commissions in the batch
    stmt = (
        select(ReferralCommission)
        .where(ReferralCommission.payout_batch_id == batch.id)
        .with_for_update()
    )
    res = await db.execute(stmt)
    commissions = list(res.scalars().all())

    for c in commissions:
        assert_commission_transition(c.status, "paid")
        c.status = "paid"
        c.paid_at = _utcnow()

    batch.status = "paid"
    batch.paid_at = _utcnow()

    await db.commit()
    await db.refresh(batch)
    return batch
