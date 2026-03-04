"""
Kinfolk API Configuration.

Uses environment variables with sensible defaults for local development.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Kinfolk API"
    app_version: str = "0.1.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8080

    # Database
    database_url: str = "sqlite:///./kinfolk.db"

    # CORS — allow Flutter app origins during development
    # Override via CORS_ORIGINS env var in production (comma-separated list)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
    ]
    # Set to True to allow all origins (development only, never in production)
    cors_allow_all: bool = False

    # Weather API (optional)
    openweather_api_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
