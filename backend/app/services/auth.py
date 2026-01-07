import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt

from app.schemas.user import MagicCodeRequest, UserCreate
from app.crud.user import get_user_by_email, create_user
from app.core.security import create_access_token
from app.core.config import settings
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

        user = await create_user(
            db=db,
            payload=user_payload,
        )

    code = f"{secrets.randbelow(1_000_000):06d}"

    user.magic_code = code
    user.magic_code_expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=MAGIC_CODE_EXPIRY_MINUTES
    )

    await db.commit()

    # TEMP: log instead of email
    print(f"[MAGIC CODE] {payload.email}: {code}")


# --------------------------------------------------
# Verify magic code
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

    if not user.magic_code_expires_at or user.magic_code_expires_at < datetime.now(timezone.utc):
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
# JWT Bearer authentication (Swagger-compatible)
# --------------------------------------------------
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a JWT access token.
    Used by protected endpoints such as /auth/me.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = await get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
