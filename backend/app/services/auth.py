import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import MagicCodeRequest, UserCreate
from app.crud.user import get_user_by_email, create_user
from app.core.security import (
    create_access_token,
    decode_access_token,
    bearer_scheme,
)
from app.db.session import get_db
from app.models.user import User

MAGIC_CODE_EXPIRY_MINUTES = 10

# --------------------------------------------------
# Request magic code
# --------------------------------------------------
async def request_magic_code(
    db: AsyncSession,
    payload: MagicCodeRequest,
) -> None:
    user = await get_user_by_email(db, payload.email)

    if not user:
        user_payload = UserCreate(
            email=payload.email,
            tier=payload.tier,
            referral_code=payload.referral_code,
            accepts_notifications=payload.accepts_notifications,
            accepted_terms=payload.accepted_terms,
        )
        user = await create_user(db=db, payload=user_payload)

    code = f"{secrets.randbelow(1_000_000):06d}"

    user.magic_code = code
    user.magic_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=MAGIC_CODE_EXPIRY_MINUTES
    )

    await db.commit()

    # TEMP: log instead of email
    print(f"[MAGIC CODE] {payload.email}: {code}")


# --------------------------------------------------
# Verify magic code (issues JWT)
# --------------------------------------------------
async def verify_magic_code(
    db: AsyncSession,
    *,
    email: str,
    code: str,
) -> str:
    user = await get_user_by_email(db, email)

    if not user or user.magic_code != code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid magic code",
        )

    if (
        not user.magic_code_expires_at
        or user.magic_code_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic code expired",
        )

    user.is_email_verified = True
    user.magic_code = None
    user.magic_code_expires_at = None

    await db.commit()

    return create_access_token(subject=user.email)


# --------------------------------------------------
# Get current authenticated user (FINAL)
# --------------------------------------------------
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a JWT access token.
    Used by protected endpoints such as /auth/me.
    """
    try:
        payload = decode_access_token(credentials.credentials)
        email: str | None = payload.get("sub")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject",
            )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
