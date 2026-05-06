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
    CORS_ORIGINS: str
    TRIP_SERVICE_URL: str = "http://trip-service:8000"
    DATA_SERVICE_URL: str = "http://data-service:8000"
    DATA_SERVICE_SECRET: str = ""
    INTERNAL_API_SECRET: str = ""
    ANALYTICS_SERVICE_URL: str = "http://analytics-service:8000"
    TRAVELPAYOUTS_API_TOKEN: str = ""
    TRAVELPAYOUTS_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 7
    TRAVELPAYOUTS_TIMEOUT_SECONDS: float = 4.0

    class Config:
        env_file = find_env_file()
        extra = "allow"


settings = Settings()  # type: ignore[call-arg]
