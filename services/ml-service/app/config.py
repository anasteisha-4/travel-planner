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
    LLM_QUALITY_ENABLED: bool = False
    LLM_PROVIDER: str = "yandex"
    LLM_MODEL: str = "qwen3.6-35b-a3b/latest"
    LLM_API_KEY: str = ""
    LLM_FOLDER_ID: str = ""
    LLM_BASE_URL: str = "https://ai.api.cloud.yandex.net/v1"
    LLM_DATA_LOGGING_ENABLED: bool = False
    LLM_TIMEOUT_SECONDS: float = 4.0
    LLM_MAX_RETRIES: int = 1
    LLM_CACHE_TTL_SECONDS: int = 60 * 60 * 24
    LLM_RECOMMENDATION_REVIEW_LIMIT: int = 10
    LLM_ITINERARY_REVIEW_VARIANTS: int = 3
    LLM_NOTES_MAX_CHARS: int = 1200
    LLM_EXTERNAL_ROUTE_MAX_TOKENS: int = 8000
    LLM_CANDIDATE_POI_ENABLED: bool = False
    LLM_EXTERNAL_ROUTE_ENABLED: bool = False
    LLM_FAIL_OPEN: bool = True
    LLM_LOG_RAW_PROMPTS: bool = False

    class Config:
        env_file = find_env_file()
        extra = "allow"


settings = Settings()  # type: ignore[call-arg]
