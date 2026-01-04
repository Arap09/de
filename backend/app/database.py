# app/database.py
# --------------------------------------------------
# Async SQLAlchemy database configuration (runtime)
# --------------------------------------------------

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# -------------------------------------------------------------------
# Async Engine (uses validated settings)
# -------------------------------------------------------------------
engine = create_async_engine(
    settings.DATABASE_URL_ASYNC,
    pool_pre_ping=True,
)

# -------------------------------------------------------------------
# Async Session Factory
# -------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -------------------------------------------------------------------
# Declarative Base (SINGLE SOURCE OF TRUTH)
# -------------------------------------------------------------------
Base = declarative_base()

# -------------------------------------------------------------------
# Dependency
# -------------------------------------------------------------------
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
