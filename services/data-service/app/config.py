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
    INTERNAL_API_SECRET: str
    OPENTRIPMAP_API_KEY: str = ""
    YANDEX_MAPS_API_TOKEN: str = ""
    YANDEX_GEOCODER_API_KEY: str = ""
    YANDEX_GEOSUGGEST_API_KEY: str = ""
    GEOAPIFY_API_KEY: str = ""

    class Config:
        env_file = find_env_file()
        extra = "allow"


settings = Settings()  # type: ignore[call-arg]
