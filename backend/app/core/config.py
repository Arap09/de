from pydantic_settings import BaseSettings


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
    DATABASE_URL: str
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

    # v1 referral rule (ACTIVE)
    DEFAULT_REFERRAL_REWARD_KES: int = 500

    # legacy / future use (NOT USED in v1)
    REFERRAL_REWARD_NDOVU_KES: int = 500

    # --------------------------------------------------
    # Human Verification
    # --------------------------------------------------
    CLOUDFLARE_TURNSTILE_SECRET: str

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
