from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import UserCreate
from app.models.user import User
from app.crud.user import (
    get_user_by_email,
    create_user,
)
from app.core.security import (
    hash_password,
    verify_password,
)


# --------------------------------------------------
# Domain exceptions
# --------------------------------------------------
class UserAlreadyExists(Exception):
    pass


class InvalidCredentials(Exception):
    pass


# --------------------------------------------------
# Registration
# --------------------------------------------------
async def register_user(
    db: AsyncSession,
    payload: UserCreate,
) -> User:
    existing = await get_user_by_email(db, payload.email)
    if existing:
        raise UserAlreadyExists("User with this email already exists")

    user = await create_user(
        db,
        email=payload.email,
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
        raise InvalidCredentials("Invalid email or password")

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentials("Invalid email or password")

    if not user.is_active:
        raise InvalidCredentials("User account is inactive")

    return user
