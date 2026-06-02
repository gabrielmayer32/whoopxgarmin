from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    whoop_client_id: str = ""
    whoop_client_secret: str = ""
    whoop_redirect_uri: str = "http://localhost:8000/whoop/callback"

    garmin_email: str = ""
    garmin_password: str = ""

    strava_client_id: str = ""
    strava_client_secret: str = ""
    strava_redirect_uri: str = "http://localhost:8000/strava/callback"

    secret_key: str = "changeme"
    database_url: str = "sqlite:///./health_data.db"

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
