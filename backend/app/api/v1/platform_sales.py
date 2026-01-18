from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.core.roles import PlatformRole
from app.core.rbac import require_platform_roles

from app.models.referral_commission import ReferralCommission
from app.models.salesperson_profile import SalespersonProfile
from app.models.payout_batch import PayoutBatch

from app.services.referral_commissions import (
    approve_commission,
    create_payout_batch_for_salesperson,
    mark_payout_batch_paid,
    reject_commission,
    require_active_salesperson_profile,
    submit_payout_batch,
)


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
    payout_batch_id: Optional[UUID]


class SalespersonProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    referral_code: str
    commission_amount_kes: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class RejectIn(BaseModel):
    reason: str = Field(min_length=2, max_length=500)


class ApproveIn(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=500)


class PayoutBatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    salesperson_user_id: UUID
    currency: str
    status: str
    total_amount_kes: int
    created_at: datetime
    submitted_at: Optional[datetime]
    paid_at: Optional[datetime]


class PayoutBatchCreateIn(BaseModel):
    currency: str = Field(default="KES", min_length=3, max_length=8)
    max_items: int = Field(default=500, ge=1, le=2000)


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
# Admin: approve/reject a commission
# --------------------------------------------------
@router.post("/commissions/{commission_id}/approve", response_model=CommissionOut)
async def admin_approve_commission(
    commission_id: UUID,
    payload: ApproveIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    __=Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN])),
):
    try:
        return await approve_commission(db, commission_id=commission_id, notes=payload.notes)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/commissions/{commission_id}/reject", response_model=CommissionOut)
async def admin_reject_commission(
    commission_id: UUID,
    payload: RejectIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    __=Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN])),
):
    try:
        return await reject_commission(db, commission_id=commission_id, reason=payload.reason)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --------------------------------------------------
# Salesperson self-view: only my commissions
# --------------------------------------------------
@router.get("/me/commissions", response_model=List[CommissionOut])
async def list_my_commissions(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await require_active_salesperson_profile(db, user_id=current_user.id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salesperson access required")

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
# Salesperson self-view: my profile
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


# --------------------------------------------------
# Salesperson self-service: payout batching
# --------------------------------------------------
@router.post("/me/payout-batches", response_model=PayoutBatchOut)
async def create_my_payout_batch(
    payload: PayoutBatchCreateIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        batch = await create_payout_batch_for_salesperson(
            db,
            salesperson_user_id=current_user.id,
            currency=payload.currency,
            max_items=payload.max_items,
        )
        return batch
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salesperson access required")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/me/payout-batches", response_model=List[PayoutBatchOut])
async def list_my_payout_batches(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await require_active_salesperson_profile(db, user_id=current_user.id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salesperson access required")

    stmt = (
        select(PayoutBatch)
        .where(PayoutBatch.salesperson_user_id == current_user.id)
        .order_by(PayoutBatch.created_at.desc())
        .limit(limit)
    )
    if status_filter:
        stmt = stmt.where(PayoutBatch.status == status_filter.strip().lower())

    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/me/payout-batches/{batch_id}", response_model=PayoutBatchOut)
async def get_my_payout_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        await require_active_salesperson_profile(db, user_id=current_user.id)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Salesperson access required")

    batch = await db.get(PayoutBatch, batch_id)
    if not batch or batch.salesperson_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return batch


@router.post("/me/payout-batches/{batch_id}/submit", response_model=PayoutBatchOut)
async def submit_my_payout_batch(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        return await submit_payout_batch(db, batch_id=batch_id, salesperson_user_id=current_user.id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# --------------------------------------------------
# Admin: mark batch paid (platform admin only)
# --------------------------------------------------
@router.post("/payout-batches/{batch_id}/mark-paid", response_model=PayoutBatchOut)
async def admin_mark_batch_paid(
    batch_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    __=Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN])),
):
    try:
        return await mark_payout_batch_paid(db, batch_id=batch_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
