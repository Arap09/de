from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate
from app.models.user import User
from app.crud.user import get_user_by_email, create_user
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    oauth2_scheme,
)
from app.db.session import get_db


# --------------------------------------------------
# Registration
# --------------------------------------------------
async def register_user(
    db: AsyncSession,
    payload: UserCreate,
) -> User:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user = await create_user(
        db=db,
        payload=payload,
        hashed_password=hash_password(payload.password),
    )

    return user


# --------------------------------------------------
# Authentication
# --------------------------------------------------
async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    # Attach JWT dynamically (not persisted)
    user.access_token = create_access_token(subject=user.email)
    return user


# --------------------------------------------------
# Current user dependency
# --------------------------------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_access_token(token)
        email: str | None = payload.get("sub")
        if not email:
            raise ValueError("Missing subject")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_email(db, email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
