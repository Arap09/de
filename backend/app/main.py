# app/main.py
# --------------------------------------------------
# Step 0: Load environment variables programmatically
# --------------------------------------------------
import os

# Async DB URL (used by FastAPI / SQLAlchemy async)
os.environ["DATABASE_URL"] = "postgresql+asyncpg://neondb_owner:password@host/neondb?sslmode=require"

# Sync DB URL (used by Alembic or sync operations)
os.environ["DATABASE_URL_SYNC"] = "postgresql://neondb_owner:password@host/neondb?sslmode=require"

# --------------------------------------------------
# Standard imports
# --------------------------------------------------
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings  # DATABASE_URL now exists
from app.api.v1.auth import router as auth_router


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
