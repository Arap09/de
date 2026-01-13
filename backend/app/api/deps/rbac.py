from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_db
from app.models.tenant_membership import TenantMembership
from app.core.roles import TenantRole
from app.core.rbac import role_at_least
from app.api.deps.tenant import get_current_tenant_id
from app.services.auth import get_current_user
from app.models.user import User


async def get_current_membership(
    current_user: User = Depends(get_current_user),
    tenant_id: UUID = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> TenantMembership:
    """
    Resolve the user's active membership for the current tenant.
    """
    result = await db.execute(
        select(TenantMembership).where(
            TenantMembership.user_id == current_user.id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.is_active.is_(True),
        )
    )

    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has no access to this tenant",
        )

    return membership


def require_role(min_role: TenantRole):
    async def checker(
        membership: TenantMembership = Depends(get_current_membership),
    ) -> TenantMembership:
        if not role_at_least(membership.role, min_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return membership

    return checker
