from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "IMEET.AI"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://imeet:devpassword@localhost:5432/imeet"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    REFRESH_SECRET: str = "change-me-refresh-secret-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Third-party API Keys (server-side only)
    OPENAI_API_KEY: str = ""
    CLAUDE_API_KEY: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPGRAM_API_KEY: str = ""

    # S3 / MinIO
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "imeet-files"

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_STANDARD_PRICE_ID: str = ""  # $19.99/mo recurring
    STRIPE_PRO_PRICE_ID: str = ""       # $49.99/mo recurring
    STRIPE_LIFETIME_PRICE_ID: str = ""  # $299 one-time
    STRIPE_TOPUP_PRICE_ID: str = ""     # $9.99 one-time (120 min)
    STRIPE_ASR_TOPUP_PRICE_ID: str = "" # $4.99 one-time (120 ASR min)

    # Email (Zoho SMTP)
    SMTP_HOST: str = "smtp.zoho.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "service@voxclar.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Voxclar"

    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Frontend URL (for Stripe redirect)
    FRONTEND_URL: str = "http://localhost:5173"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
