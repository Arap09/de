from uuid import UUID

from fastapi import Depends, Header, HTTPException, status


async def get_current_tenant_id(
    x_tenant_id: str | None = Header(default=None),
) -> UUID:
    if not x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Tenant-Id header is required",
        )

    try:
        return UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant id",
        )
