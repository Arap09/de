# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --------------------------------------------------
    # Application
    # --------------------------------------------------
    APP_NAME: str = "POSTIKA"
    ENV: str = "development"

    # --------------------------------------------------
    # Security
    # --------------------------------------------------
    SECRET_KEY: str

    # --------------------------------------------------
    # Database & Cache
    # --------------------------------------------------
    DATABASE_URL_ASYNC: str      # asyncpg (FastAPI runtime)
    DATABASE_URL_SYNC: str       # psycopg (Alembic, psql)
    REDIS_URL: str

    # --------------------------------------------------
    # Celery
    # --------------------------------------------------
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # --------------------------------------------------
    # Frontend / Media
    # --------------------------------------------------
    FRONTEND_URL: str
    MEDIA_DOMAIN: str

    # --------------------------------------------------
    # Business Rules
    # --------------------------------------------------
    TRIAL_PERIOD_DAYS: int = 7
    DEFAULT_REFERRAL_REWARD_KES: int = 500
    REFERRAL_REWARD_NDOVU_KES: int = 500

    # --------------------------------------------------
    # Human Verification
    # --------------------------------------------------
    CLOUDFLARE_TURNSTILE_SECRET: str

    # --------------------------------------------------
    # Pydantic v2 config
    # --------------------------------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="forbid",
    )


settings = Settings()
