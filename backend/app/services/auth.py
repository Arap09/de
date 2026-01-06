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
