from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from app.core.roles import TenantRole


class TenantMembershipRead(BaseModel):
    id: UUID
    user_id: UUID
    tenant_id: UUID
    role: TenantRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
