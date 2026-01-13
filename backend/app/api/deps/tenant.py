from uuid import UUID

from fastapi import Header, HTTPException, status


async def get_current_tenant_id(
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
) -> UUID:
    """
    Extract and validate tenant ID from request headers.

    Responsibilities:
    - Require X-Tenant-Id header
    - Validate UUID format
    - Return UUID instance

    Does NOT:
    - Decode JWT
    - Perform membership checks
    """
    try:
        return UUID(x_tenant_id)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid X-Tenant-Id",
        )
