from fastapi import APIRouter, Depends

from app.core.rbac import require_roles
from app.core.roles import TenantRole

router = APIRouter(prefix="/rbac-test", tags=["RBAC Test"])


@router.get("/owner-only")
async def owner_only(
    tenant_user=Depends(require_roles([TenantRole.OWNER])),
):
    return {
        "message": "RBAC check passed",
        "role": tenant_user.role,
    }
