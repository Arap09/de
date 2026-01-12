# app/db/session.py

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# --------------------------------------------------
# 🔑 IMPORTANT: Import models to register metadata
# --------------------------------------------------
import app.models  # noqa: F401


# --------------------------------------------------
# Async SQLAlchemy Engine (FastAPI runtime)
# --------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    pool_pre_ping=True,
    future=True,
)

# --------------------------------------------------
# Async session factory
# --------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# --------------------------------------------------
# FastAPI dependency
# --------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
