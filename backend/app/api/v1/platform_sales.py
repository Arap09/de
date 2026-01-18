from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.core.roles import PlatformRole
from app.core.rbac import require_platform_roles

from app.models.referral_commission import ReferralCommission


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
