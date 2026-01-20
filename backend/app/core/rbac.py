# app/core/rbac.py
from __future__ import annotations

from typing import Iterable, Set

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.roles import PlatformRole, TenantRole
from app.api.deps import get_current_membership  # NOTE: deps is a module, not a package
from app.db.session import get_db
from app.models.platform_membership import PlatformMembership
from app.models.tenant_membership import TenantMembership
from app.models.user import User
from app.services.auth import get_current_user


# ------------------------------------------
# Tenant role hierarchy for "at least" checks
# Useful for role escalation prevention
# ------------------------------------------
ROLE_HIERARCHY: dict[TenantRole, int] = {
    TenantRole.OWNER: 5,
    TenantRole.ADMIN: 4,
    TenantRole.MANAGER: 3,
    TenantRole.AGENT: 2,
    TenantRole.VIEWER: 1,
}


def role_at_least(user_role: TenantRole, required_role: TenantRole) -> bool:
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

    IMPORTANT:
    This uses app.api.deps.get_current_membership which is tenant resolution
    via X-Tenant-Id header.
    """
    allowed_set: Set[TenantRole] = set(allowed_roles)

    async def role_checker(
        membership: TenantMembership = Depends(get_current_membership),
    ) -> TenantMembership:
        if membership.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return membership

    return role_checker


# ------------------------------------------
# Platform RBAC enforcement dependency
# ------------------------------------------
def require_platform_roles(allowed_roles: Iterable[PlatformRole]):
    """
    FastAPI dependency to enforce that the current user has an active platform membership
    with one of the allowed platform roles.

    Usage:
        __ = Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN]))
    """
    allowed_values: Set[str] = {r.value for r in allowed_roles}

    async def _dep(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
    ) -> PlatformMembership:
        stmt = select(PlatformMembership).where(
            PlatformMembership.user_id == current_user.id,
        )
        res = await db.execute(stmt)
        pm = res.scalar_one_or_none()

        if not pm or not pm.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Platform access required",
            )

        role_val = (pm.role or "").strip().lower()
        if role_val not in allowed_values:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient platform permissions",
            )

        return pm

    return _dep
