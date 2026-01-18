from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.core.roles import PlatformRole
from app.core.rbac import require_platform_roles

from app.models.referral_commission import ReferralCommission
from app.models.salesperson_profile import SalespersonProfile


router = APIRouter(prefix="/platform/sales", tags=["Platform Sales"])


class CommissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    salesperson_user_id: UUID
    tenant_id: UUID
    subscription_id: Optional[UUID]
    billing_event: str
    amount_kes: int
    currency: str
    status: str
    source_referral_code: str
    created_at: datetime
    paid_at: Optional[datetime]
    notes: Optional[str]


class SalespersonProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    referral_code: str
    commission_amount_kes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------
# Admin view: list all commissions (platform admin only)
# --------------------------------------------------
@router.get("/commissions", response_model=List[CommissionOut])
async def list_commissions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    __=Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN])),
):
    stmt = select(ReferralCommission).order_by(ReferralCommission.created_at.desc()).limit(limit)
    if status_filter:
        stmt = stmt.where(ReferralCommission.status == status_filter.strip().lower())
    res = await db.execute(stmt)
    return list(res.scalars().all())


# --------------------------------------------------
# Salesperson self-view: only my commissions (NO platform admin required)
# --------------------------------------------------
@router.get("/me/commissions", response_model=List[CommissionOut])
async def list_my_commissions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Gate access by presence of an active salesperson profile
    stmt_profile = select(SalespersonProfile).where(SalespersonProfile.user_id == current_user.id)
    profile_res = await db.execute(stmt_profile)
    profile = profile_res.scalar_one_or_none()

    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesperson access required",
        )

    stmt = (
        select(ReferralCommission)
        .where(ReferralCommission.salesperson_user_id == current_user.id)
        .order_by(ReferralCommission.created_at.desc())
        .limit(limit)
    )

    if status_filter:
        stmt = stmt.where(ReferralCommission.status == status_filter.strip().lower())

    res = await db.execute(stmt)
    return list(res.scalars().all())


# --------------------------------------------------
# Salesperson self-view: my profile (referral code, commission rate)
# --------------------------------------------------
@router.get("/me/profile", response_model=SalespersonProfileOut)
async def get_my_sales_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt_profile = select(SalespersonProfile).where(SalespersonProfile.user_id == current_user.id)
    profile_res = await db.execute(stmt_profile)
    profile = profile_res.scalar_one_or_none()

    if not profile or not profile.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesperson access required",
        )

    return profile
