from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate
from app.crud.user import (
    get_user_by_email,
    get_user_by_phone,
    create_user,
)
from app.core.security import verify_password, hash_password
from app.utils.passwords import validate_password_rules, generate_password


# -------------------------
# Exceptions (domain-level)
# -------------------------

class AuthError(Exception):
    pass


class UserAlreadyExists(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


# -------------------------
# Signup
# -------------------------

async def register_user(
    db: AsyncSession,
    payload: UserCreate,
    *,
    referral_code: Optional[str] = None,
    referred_by_id: Optional[int] = None,
) -> User:
    # Enforce unique email
    existing_email = await get_user_by_email(db, payload.email)
    if existing_email:
        raise UserAlreadyExists("Email already registered")

    # Enforce unique phone
    existing_phone = await get_user_by_phone(db, payload.phone_number)
    if existing_phone:
        raise UserAlreadyExists("Phone number already registered")

    # Password handling
    if payload.password:
        validate_password_rules(payload.password)
        password = payload.password
    else:
        password = generate_password()

    hashed_password = hash_password(password)

    user = await create_user(
        db,
        payload,
        hashed_password=hashed_password,
        referral_code=referral_code,
        referred_by_id=referred_by_id,
    )

    return user


# -------------------------
# Login
# -------------------------

async def authenticate_user(
    db: AsyncSession,
    *,
    email: str,
    password: str
) -> User:
    user = await get_user_by_email(db, email)
    if not user:
        raise InvalidCredentials("Invalid email or password")

    if not user.is_active:
        raise InvalidCredentials("Account is disabled")

    if not verify_password(password, user.hashed_password):
        raise InvalidCredentials("Invalid email or password")

    return user
