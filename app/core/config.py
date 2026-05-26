"""
Application Configuration
==========================
Reads environment variables (from .env or shell).
"""

from __future__ import annotations
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Generative AI (Gemini)
    google_api_key: str = ""

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    data_dir: str = "data"
    max_upload_bytes: int = 200 * 1024 * 1024
    max_pdf_pages: int = 500
    auth_token_ttl_seconds: int = 24 * 60 * 60

    # Distributed worker
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    worker_concurrency: int = 2
    task_time_limit_seconds: int = 60 * 60

settings = Settings()
