from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class TierEnum(str, Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


# --------------------------------------------------
# NEW: Email-only request for staff/sales/platform
# --------------------------------------------------
class MagicCodeRequestStaff(BaseModel):
    email: EmailStr


# --------------------------------------------------
# NEW: Tenant OWNER entrypoint (tier + ToS required)
# Notifications optional (global), referral optional
# --------------------------------------------------
class MagicCodeRequestTenant(BaseModel):
    email: EmailStr
    tier: TierEnum = Field(..., description="Tenant tier chosen on homepage")
    referral_code: Optional[str] = None
    accepts_notifications: bool = False
    accepted_terms: bool = Field(..., description="Must be true to proceed")

    @field_validator("accepted_terms")
    @classmethod
    def validate_accepted_terms(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("accepted_terms must be true")
        return v


# Backward compat
class MagicCodeRequest(MagicCodeRequestTenant):
    pass


class MagicCodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class UserCreate(BaseModel):
    email: EmailStr
    tier: TierEnum
    referral_code: Optional[str] = None
    accepts_notifications: bool = False
    accepted_terms: bool

    @field_validator("accepted_terms")
    @classmethod
    def validate_accepted_terms(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("accepted_terms must be true")
        return v


class UserProfileUpdate(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    country_code: str = Field(..., max_length=5)
    phone_number: str = Field(..., max_length=20)


class NotificationsPreferenceUpdate(BaseModel):
    accepts_notifications: bool = Field(..., description="Global notifications preference true/false")


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    tier: TierEnum
    accepts_notifications: bool
    is_email_verified: bool
    trial_expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
