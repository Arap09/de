from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User

from app.api.deps import get_current_membership, require_consent
from app.core.rbac import require_roles
from app.core.roles import TenantRole
from app.models.tenant import Tenant

from app.services.invitations import (
    create_invitation,
    list_invitations,
    revoke_invitation,
    accept_invitation,
)


router = APIRouter(prefix="/invitations", tags=["Invitations"])


# ---------------------------
# Pydantic Schemas (stable)
# ---------------------------
class InvitationCreate(BaseModel):
    email: EmailStr
    role: TenantRole = Field(..., description="Tenant role to assign on acceptance")


class InvitationAccept(BaseModel):
    token: str = Field(..., min_length=20)


class InvitationOut(BaseModel):
    """
    Canonical invitation payload. Used consistently by create/list/revoke.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    inviter_user_id: Optional[UUID]
    email: str
    role: str
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime


class InvitationSendResponse(BaseModel):
    invitation: InvitationOut
    email_sent: bool
    accept_url: str


class InvitationsListResponse(BaseModel):
    invitations: List[InvitationOut]


class InvitationRevokeResponse(BaseModel):
    invitation: InvitationOut
    revoked: bool


class AcceptResult(BaseModel):
    tenant_id: UUID
    role: str
    membership_created: bool = True


# --------------------------------------------------
# Create invitation (OWNER/ADMIN only, consent required)
# --------------------------------------------------
@router.post(
    "",
    response_model=InvitationSendResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_invitation(
    payload: InvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    membership=Depends(get_current_membership),
    _: bool = Depends(require_consent),
    __=Depends(require_roles([TenantRole.OWNER, TenantRole.ADMIN])),
):
    """
    Create and send an invitation to join the current tenant.

    Requires:
    - Bearer token
    - X-Tenant-Id
    - Consent accepted
    - Role: OWNER or ADMIN
    """
    tenant = await db.get(Tenant, membership.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found for membership")

    invitation = await create_invitation(
        db,
        tenant=tenant,
        inviter=current_user,
        email=str(payload.email),
        role=payload.role.value,  # store canonical string (e.g. "admin", "agent")
    )

    accept_url = f"{settings.APP_BASE_URL.rstrip('/')}/accept-invitation?token={invitation.token}"

    return {
        "invitation": invitation,
        "email_sent": True,
        "accept_url": accept_url,
    }


# --------------------------------------------------
# List invitations (OWNER/ADMIN only, consent required)
# --------------------------------------------------
@router.get("", response_model=InvitationsListResponse)
async def list_all_invitations(
    status_filter: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    membership=Depends(get_current_membership),
    _: bool = Depends(require_consent),
    __=Depends(require_roles([TenantRole.OWNER, TenantRole.ADMIN])),
):
    """
    List invitations for the current tenant.

    status_filter: pending|accepted|revoked|expired|all
    """
    invites = await list_invitations(
        db,
        tenant_id=membership.tenant_id,
        status_filter=status_filter,
        limit=limit,
    )
    return {"invitations": invites}


# --------------------------------------------------
# Revoke invitation (OWNER/ADMIN only, consent required)
# --------------------------------------------------
@router.post("/{invitation_id}/revoke", response_model=InvitationRevokeResponse)
async def revoke(
    invitation_id: UUID,
    db: AsyncSession = Depends(get_db),
    membership=Depends(get_current_membership),
    _: bool = Depends(require_consent),
    __=Depends(require_roles([TenantRole.OWNER, TenantRole.ADMIN])),
):
    """
    Revoke a pending invitation (idempotent).
    """
    invitation = await revoke_invitation(
        db,
        tenant_id=membership.tenant_id,
        invitation_id=invitation_id,
    )
    return {
        "invitation": invitation,
        "revoked": invitation.revoked_at is not None,
    }


# --------------------------------------------------
# Accept invitation (AUTH ONLY; EXEMPT FROM CONSENT)
# --------------------------------------------------
@router.post("/accept", response_model=AcceptResult)
async def accept(
    payload: InvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Accept an invitation using its token.

    IMPORTANT:
    - This endpoint is intentionally NOT protected by:
      - get_current_membership (user isn't a member yet)
      - require_consent (consent happens after membership)
      - require_roles

    After acceptance, the user should:
    - send X-Tenant-Id header
    - call /auth/consent/status
    - if required, call /auth/consent/accept
    """
    membership = await accept_invitation(
        db,
        token=payload.token,
        current_user=current_user,
    )

    return {
        "tenant_id": membership.tenant_id,
        "role": membership.role,
        "membership_created": True,
    }
