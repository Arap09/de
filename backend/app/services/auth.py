import secrets
from datetime import datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.user import MagicCodeRequest, UserCreate
from app.crud.user import get_user_by_email, create_user
from app.core.security import create_access_token


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
    user.magic_code_expires_at = datetime.utcnow() + timedelta(
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

    if not user.magic_code_expires_at or user.magic_code_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic code expired",
        )

    user.is_email_verified = True
    user.magic_code = None
    user.magic_code_expires_at = None

    await db.commit()

    return create_access_token(subject=user.email)
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.crud.user import get_user_by_email


# Used by Swagger UI and protected routes
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/verify-code"
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a JWT access token.
    Used by protected endpoints such as /auth/me.
    """

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        email: str | None = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(db, email)
    if user is None:
        raise credentials_exception

    return user
