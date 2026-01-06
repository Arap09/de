from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import (
    MagicCodeRequest,
    MagicCodeVerify,
    UserRead,
)
from app.services.auth import (
    request_magic_code,
    verify_magic_code,
    get_current_user,
)
from app.models.user import User


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
# Verify magic code
# --------------------------------------------------
@router.post("/verify-code")
async def verify_code(
    payload: MagicCodeVerify,
    db: AsyncSession = Depends(get_db),
):
    access_token = await verify_magic_code(
        db,
        email=payload.email,
        code=payload.code,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


# --------------------------------------------------
# Current user
# --------------------------------------------------
@router.get(
    "/me",
    response_model=UserRead,
)
async def me(
    current_user: User = Depends(get_current_user),
):
    return current_user
