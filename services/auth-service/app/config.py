"""
Configuration settings for Auth Service
"""

from pathlib import Path

from pydantic_settings import BaseSettings


def find_env_file():
    config_path = Path(__file__).resolve()
    for parent in config_path.parents:
        env_file = parent / ".env"
        if env_file.exists():
            return str(env_file)
    return None


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: str

    YANDEX_CLIENT_ID: str | None = None
    YANDEX_CLIENT_SECRET: str | None = None
    YANDEX_REDIRECT_URI: str | None = None

    class Config:
        env_file = find_env_file()
        extra = "allow"


settings = Settings()
