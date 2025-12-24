from datetime import datetime, timedelta
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings


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
        audience=None,
        options={"verify_aud": False},
    )
