from sqlalchemy import select
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.tenant_membership import TenantMembership

# Consent model
from app.models.user_consent import UserConsent


# --------------------------------------------------
# POLICY: Required terms per role
# --------------------------------------------------
def get_required_terms_for_role(role: str) -> str | None:
    """
    Return the required terms version for a given role.

    IMPORTANT:
    - This is POLICY, not enforcement
    - Returning None means no consent is required
    - Versioning allows future legal updates without logic changes
    """
    return {
        "OWNER": "customer_v1",
        "ADMIN": "staff_v1",
        "MANAGER": "staff_v1",
        "AGENT": "agent_v1",
        "SALES": "sales_v1",
        # SUPER_ADMIN intentionally excluded
    }.get(role)


async def get_current_membership(
    tenant_id: str = Header(..., alias="X-Tenant-Id"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> TenantMembership:
    """
    Resolve the user's active membership for the given tenant.

    This function is AUTH + TENANT resolution only.
    No consent or business logic here.
    """

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


# --------------------------------------------------
# POST-AUTH CONSENT ENFORCEMENT (ROLE-SCOPED)
# --------------------------------------------------
async def require_consent(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
):
    """
    Enforce role-specific consent AFTER authentication.

    DESIGN GUARANTEES:
    - Never blocks magic code login
    - Never creates consent
    - Only gates protected resources
    """

    # Determine which terms apply to this role
    required_terms = get_required_terms_for_role(membership.role)

    # Some roles may not require consent
    if required_terms is None:
        return True

    stmt = (
        select(UserConsent)
        .where(UserConsent.user_id == current_user.id)
        .where(UserConsent.tenant_id == membership.tenant_id)
        .where(UserConsent.role == membership.role)
        .where(UserConsent.terms_version == required_terms)
        .where(UserConsent.revoked_at.is_(None))
    )

    result = await db.execute(stmt)
    consent = result.scalar_one_or_none()

    if not consent:
        # Frontend must redirect user to accept role-specific terms
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "CONSENT_REQUIRED",
                "role": membership.role,
                "terms_version": required_terms,
            },
        )

    return True
