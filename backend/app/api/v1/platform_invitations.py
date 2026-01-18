from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.auth import get_current_user
from app.models.user import User

from app.core.roles import PlatformRole
from app.core.rbac import require_platform_roles  # you will add this helper (below)

from app.models.platform_invitation import PlatformInvitation
from app.services.platform_invitations import create_platform_invitation, accept_platform_invitation


router = APIRouter(prefix="/platform/invitations", tags=["Platform Invitations"])


class PlatformInvitationCreate(BaseModel):
    email: EmailStr
    invitee_type: str = Field(..., description="platform_admin|salesperson")
    platform_role: Optional[PlatformRole] = Field(default=None, description="Required if invitee_type=platform_admin")


class PlatformInvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    inviter_user_id: Optional[UUID]
    email: str
    invitee_type: str
    platform_role: Optional[str]
    token: str
    expires_at: datetime
    accepted_at: Optional[datetime]
    revoked_at: Optional[datetime]
    created_at: datetime


class PlatformInvitationSendResponse(BaseModel):
    invitation: PlatformInvitationOut
    email_sent: bool


class PlatformInvitationAccept(BaseModel):
    token: str = Field(..., min_length=20)


class PlatformAcceptResult(BaseModel):
    invitee_type: str
    platform_role: Optional[str] = None
    platform_membership_created: bool = False
    salesperson_profile_created: bool = False
    referral_code: Optional[str] = None


@router.post("", response_model=PlatformInvitationSendResponse, status_code=status.HTTP_201_CREATED)
async def create_platform_invite(
    payload: PlatformInvitationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    __=Depends(require_platform_roles([PlatformRole.SUPER_ADMIN, PlatformRole.PLATFORM_ADMIN])),
):
    inv = await create_platform_invitation(
        db,
        inviter=current_user,
        email=str(payload.email),
        invitee_type=payload.invitee_type,
        platform_role=payload.platform_role.value if payload.platform_role else None,
    )
    return {"invitation": inv, "email_sent": True}


@router.post("/accept", response_model=PlatformAcceptResult)
async def accept_platform_invite(
    payload: PlatformInvitationAccept,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await accept_platform_invitation(db, token=payload.token, current_user=current_user)
