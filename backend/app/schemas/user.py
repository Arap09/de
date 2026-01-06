from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class TierEnum(str, Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


# --------------------------------------------------
# Email-only signup
# --------------------------------------------------
class MagicCodeRequest(BaseModel):
    email: EmailStr
    tier: TierEnum = TierEnum.sungura
    referral_code: Optional[str] = None
    accepts_notifications: bool = True
    accepted_terms: bool = Field(
        ...,
        description="Must be true to proceed"
    )


class MagicCodeVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


# --------------------------------------------------
# Profile completion (post-login)
# --------------------------------------------------
class UserProfileUpdate(BaseModel):
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    country_code: str = Field(..., max_length=5)
    phone_number: str = Field(..., max_length=20)


# --------------------------------------------------
# API response
# --------------------------------------------------
class UserRead(BaseModel):
    id: str
    email: EmailStr
    tier: TierEnum
    is_email_verified: bool
    trial_expires_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
