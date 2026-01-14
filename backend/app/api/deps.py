from sqlalchemy import select
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.tenant_membership import TenantMembership


async def get_current_membership(
    tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TenantMembership:

    stmt = (
        select(TenantMembership)
        .where(TenantMembership.tenant_id == tenant_id)
        .where(TenantMembership.user_id == current_user.id)
    )

    result = await db.execute(stmt)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this tenant",
        )

    if not membership.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User role is inactive or revoked",
        )

    return membership
