from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.referral_commission import ReferralCommission
from app.models.salesperson_profile import SalespersonProfile
from app.models.tenant import Tenant


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_commission_for_subscription(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    billing_event: str,
    subscription_id: Optional[UUID] = None,
    amount_kes_override: Optional[int] = None,
) -> Optional[ReferralCommission]:
    """
    POSTIKA canonical commission creation hook.

    CALL THIS ONLY AFTER:
      - subscription payment is confirmed
      - subscription is activated or renewed

    Returns:
      - ReferralCommission if created
      - None if:
          * tenant has no referral_code_used
          * referral code does not belong to an active salesperson
          * commission already exists (idempotency)
    """

    # --------------------------------------------------
    # 1) Load tenant
    # --------------------------------------------------
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        return None

    referral_code = tenant.referral_code_used
    if not referral_code:
        return None

    referral_code = referral_code.strip().upper()
    if not referral_code:
        return None

    # --------------------------------------------------
    # 2) Resolve salesperson
    # --------------------------------------------------
    stmt_sp = select(SalespersonProfile).where(
        SalespersonProfile.referral_code == referral_code,
        SalespersonProfile.is_active.is_(True),
    )
    sp_res = await db.execute(stmt_sp)
    salesperson = sp_res.scalar_one_or_none()

    if not salesperson:
        return None

    # --------------------------------------------------
    # 3) Idempotency guard (IMPORTANT)
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 4) Determine commission amount
    # --------------------------------------------------
    amount_kes = (
        int(amount_kes_override)
        if amount_kes_override is not None
        else int(
            salesperson.commission_amount_kes
            or getattr(settings, "DEFAULT_REFERRAL_REWARD_KES", 500)
        )
    )

    # --------------------------------------------------
    # 5) Create commission ledger entry
    # --------------------------------------------------
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
