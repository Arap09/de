from datetime import datetime, timedelta
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.crud.user import get_user_by_id


# --------------------------------------------------
# Password hashing
# --------------------------------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    """
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a bcrypt hash.
    """
    return pwd_context.verify(password, hashed)


# --------------------------------------------------
# JWT handling
# --------------------------------------------------
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login"
)


def create_access_token(
    subject: str,
    expires_minutes: int = 60,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Create a signed JWT access token.
    """
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)

    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": settings.APP_NAME,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.
    Raises JWTError if invalid or expired.
    """
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
        options={"verify_aud": False},
    )


# --------------------------------------------------
# Current user dependency
# --------------------------------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Resolve the current authenticated user from JWT.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        subject: str | None = payload.get("sub")
        if subject is None:
            raise credentials_exception
        user_id = int(subject)
    except (JWTError, ValueError):
        raise credentials_exception

    user = await get_user_by_id(db, user_id)
    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user
