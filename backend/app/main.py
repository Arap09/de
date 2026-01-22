# app/main.py

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

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.platform_sales import router as platform_sales_router

# ✅ Unified invitations router (tenant + platform + salesperson)
from app.api.v1.invitations import router as invitations_router

# --------------------------------------------------
# 🔑 Force model registration at application startup
# --------------------------------------------------
import app.models  # noqa: F401


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
    app.include_router(auth_router, prefix="/api/v1")

    # ✅ Keep platform sales (commissions/payouts) as-is
    app.include_router(platform_sales_router, prefix="/api/v1")

    # ✅ Invitations are now unified; this powers tenant staff + platform staff + salespeople invites
    app.include_router(invitations_router, prefix="/api/v1")

    # ❌ DO NOT include platform_invitations_router anymore.
    # This removes /api/v1/platform/invitations* endpoints from Swagger,
    # while unified invitations still call the platform invitation service internally.

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
