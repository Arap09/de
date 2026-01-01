from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
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
