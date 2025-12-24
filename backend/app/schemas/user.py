from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class TierEnum(str, Enum):
    sungura = "sungura"
    swara = "swara"
    ndovu = "ndovu"


# -------------------------
# Base schema (shared)
# -------------------------
class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., max_length=50)
    last_name: str = Field(..., max_length=50)
    country_code: str = Field(..., max_length=5)
    phone_number: str = Field(..., max_length=20)


# -------------------------
# Create (signup)
# -------------------------
class UserCreate(UserBase):
    password: Optional[str] = Field(
        None,
        description="Plain password. If omitted, server may generate one."
    )
    tier: TierEnum = TierEnum.sungura
    referral_code: Optional[str] = None
    accepts_notifications: bool = True
    accepted_terms: bool = Field(
        ...,
        description="Must be true to complete signup"
    )


# -------------------------
# Login
# -------------------------
class UserLogin(BaseModel):
    email: EmailStr
    password: str


# -------------------------
# Internal DB representation
# -------------------------
class UserInDB(UserBase):
    id: int
    is_active: bool
    is_email_verified: bool
    tier: TierEnum
    referral_code: str
    referred_by_id: Optional[int]

    trial_starts_at: datetime
    trial_expires_at: datetime

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# -------------------------
# API response (safe)
# -------------------------
class UserRead(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    tier: TierEnum
    is_email_verified: bool
    trial_expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True
