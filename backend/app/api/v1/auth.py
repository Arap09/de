from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import UserCreate, UserLogin, UserRead
from app.services.auth import (
    register_user,
    authenticate_user,
    get_current_user,
    UserAlreadyExists,
    InvalidCredentials,
)
from app.models.user import User


router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


# --------------------------------------------------
# Register
# --------------------------------------------------
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await register_user(db, payload)
    except UserAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return user


# --------------------------------------------------
# Login
# --------------------------------------------------
@router.post("/login")
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    try:
        user = await authenticate_user(
            db,
            email=payload.email,
            password=payload.password,
        )
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    return {
        "access_token": user.access_token,
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
