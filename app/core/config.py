from functools import lru_cache
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    APP_NAME: str = "Kenang"
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_URL: str = "http://localhost:8000"

    DATABASE_URL: str
    DATABASE_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "ap-southeast-1"
    S3_BUCKET_NAME: str = "kenang-dev"

    OPENAI_API_KEY: Optional[str] = None

    MIDTRANS_SERVER_KEY: Optional[str] = None
    MIDTRANS_CLIENT_KEY: Optional[str] = None
    MIDTRANS_IS_PRODUCTION: bool = False

    SMS_PROVIDER: str = "fazpass"
    FAZPASS_API_KEY: Optional[str] = None
    FAZPASS_GATEWAY_KEY: Optional[str] = None

    FIREBASE_CREDENTIALS_PATH: Optional[str] = None

    SENTRY_DSN: Optional[str] = None

    OTP_EXPIRY_MINUTES: int = 5
    OTP_MAX_ATTEMPTS_PER_HOUR: int = 5
    OTP_LENGTH: int = 6

    FREE_TIER_MAX_CIRCLES: int = 3
    FREE_TIER_MAX_PHOTOS: int = 50
    FREE_TIER_MAX_STORIES: int = 10
    PERSONAL_TIER_MAX_CIRCLES: int = 10
    PERSONAL_TIER_MAX_PHOTOS: int = 200
    PLUS_TIER_MAX_CIRCLES: int = 25
    PLUS_TIER_MAX_PHOTOS: int = 1000

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v.startswith(("postgresql", "postgres")):
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return v

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
