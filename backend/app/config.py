"""
Kinfolk API Configuration.

Uses environment variables with sensible defaults for local development.
"""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


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
    database_encryption_key: str = "change-me-in-env"

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

    # Voice / wake word
    wake_word_sensitivity: float = 0.5
    wake_word_engine: str = "openwakeword"
    audio_sample_rate: int = 16000
    audio_channels: int = 1

    # Speech-to-text (STT)
    stt_mode: str = "local"
    openai_api_key: Optional[str] = None
    vosk_model_path: str = "./models/vosk-model-en-us"

    # Text-to-Speech (TTS)
    tts_engine: str = "nanotts"  # "nanotts" (offline) or "gtts" (network)
    tts_speed: float = 1.0
    tts_volume: float = 0.8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
