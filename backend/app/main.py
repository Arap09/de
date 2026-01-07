import os

# Async DB URL (used by FastAPI / SQLAlchemy async)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://neondb_owner:password@host/neondb?sslmode=require"

# Sync DB URL (used by Alembic or sync operations)
os.environ["DATABASE_URL_SYNC"] = "postgresql://neondb_owner:password@host/neondb?sslmode=require"

# --------------------------------------------------
# Standard imports
# --------------------------------------------------
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.services.auth import get_current_user, get_current_user_swagger
from app.models.user import User
from app.db.session import get_db

# --------------------------------------------------
# Security: Swagger Bearer token
# --------------------------------------------------
bearer_scheme = HTTPBearer()

async def get_current_user_swagger_main(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Helper for Swagger UI to authenticate JWT bearer token.
    Can be used in docs as a security dependency.
    """
    token = credentials.credentials
    return await get_current_user(token=token, db=db)


def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
    )

    # --------------------------------------------------
    # CORS settings
    # --------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Development only
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # --------------------------------------------------
    # API Routers
    # --------------------------------------------------
    app.include_router(
        auth_router,
        prefix="/api/v1",
    )

    # --------------------------------------------------
    # Health check
    # --------------------------------------------------
    @app.get("/", tags=["Health"])
    async def root():
        return {
            "status": "ok",
            "message": "POSTIKA backend is live",
        }

    return app


app = create_application()
