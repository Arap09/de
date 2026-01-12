from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    MagicCodeRequest,
    MagicCodeVerify,
)
from app.services.auth import (
    request_magic_code,
    verify_magic_code,
    get_current_user,
)
from app.models.user import User

# NEW IMPORTS FOR TENANT RBAC
from app.api.deps.rbac import get_current_membership
from app.models.tenant_membership import TenantMembership


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# --------------------------------------------------
# Request magic code
# --------------------------------------------------
@router.post(
    "/request-code",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def request_code(
    payload: MagicCodeRequest,
    db: AsyncSession = Depends(get_db),
):
    await request_magic_code(db, payload)


# --------------------------------------------------
# Verify magic code (login / first signup)
# --------------------------------------------------
@router.post("/verify-code")
async def verify_code(
    payload: MagicCodeVerify,
    db: AsyncSession = Depends(get_db),
):
    """
    This endpoint:
    - Verifies the magic code
    - Creates user if needed
    - Creates tenant if first login
    - Assigns OWNER role on tenant creation
    - Returns JWT access token
    """

    result = await verify_magic_code(
        db,
        email=payload.email,
        code=payload.code,
    )

    return {
        "access_token": result["access_token"],
        "token_type": "bearer",
    }


# --------------------------------------------------
# Current authenticated user (TENANT-AWARE)
# --------------------------------------------------
@router.get("/me")
async def me(
    current_user: User = Depends(get_current_user),
    membership: TenantMembership = Depends(get_current_membership),
):
    """
    Tenant-aware identity endpoint.

    Requires:
    - Authorization: Bearer <token>
    - X-Tenant-Id header
    """

    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
        },
        "tenant": {
            "id": membership.tenant_id,
        },
        "role": membership.role,
    }
