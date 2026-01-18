from fastapi import Depends, HTTPException, status
from typing import Iterable

from app.core.roles import TenantRole
from app.api.deps import get_current_membership

# ------------------------------------------
# Role hierarchy for "at least" checks
# Useful for role escalation prevention
# ------------------------------------------
ROLE_HIERARCHY: dict[TenantRole, int] = {
    TenantRole.OWNER: 5,
    TenantRole.ADMIN: 4,
    TenantRole.MANAGER: 3,
    TenantRole.AGENT: 2,
    TenantRole.VIEWER: 1,
}


def role_at_least(
    user_role: TenantRole,
    required_role: TenantRole,
) -> bool:
    """
    Returns True if user_role >= required_role in hierarchy.
    Useful for hierarchical checks like role assignment restrictions.
    """
    return ROLE_HIERARCHY[user_role] >= ROLE_HIERARCHY[required_role]


# ------------------------------------------
# Hard RBAC enforcement dependency
# Use for ALL tenant-scoped protected endpoints
# ------------------------------------------
def require_roles(allowed_roles: Iterable[TenantRole]):
    """
    FastAPI dependency to enforce that the current tenant membership
    has one of the allowed roles.
    """

    async def role_checker(
        membership=Depends(get_current_membership),
    ):
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return membership

    return role_checker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.models.platform_membership import PlatformMembership


def require_platform_roles(allowed_roles):
    """
    FastAPI dependency to enforce that the current user has an active platform membership
    with one of the allowed platform roles (e.g. SUPER_ADMIN, PLATFORM_ADMIN).

    Usage:
        __ = Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN]))
    """

    async def _dep(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ):
        stmt = select(PlatformMembership).where(PlatformMembership.user_id == current_user.id)
        res = await db.execute(stmt)
        pm = res.scalar_one_or_none()

        if not pm or not pm.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform access required",
            )

        allowed = {r.value if hasattr(r, "value") else str(r) for r in allowed_roles}
        if pm.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient platform permissions",
            )

        return True

    return _dep
