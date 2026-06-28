"""
Application Configuration
==========================
Reads environment variables (from .env or shell).
"""

from __future__ import annotations
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM provider
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    google_api_key: str = ""
    gemini_model: str = "gemini-3-flash-preview"

    # App
    app_env: str = "development"
    log_level: str = "INFO"
    data_dir: str = "data"
    database_url: str = ""
    document_store: str = "local"
    s3_bucket: str = ""
    s3_endpoint_url: str = ""
    s3_region: str = "us-east-1"
    allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    max_upload_bytes: int = 200 * 1024 * 1024
    max_pdf_pages: int = 500
    auth_token_ttl_seconds: int = 24 * 60 * 60
    auth_cookie_secure: bool = False
    auth_demo_enabled: bool = False
    auth_rate_limit: int = 10
    auth_rate_window_seconds: int = 300

    # Distributed worker
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    worker_concurrency: int = 2
    worker_lease_seconds: int = 120
    processing_max_attempts: int = 3
    processing_deadline_seconds: int = 3600
    retry_base_seconds: int = 2
    task_time_limit_seconds: int = 60 * 60

    @model_validator(mode="after")
    def production_security(self):
        if self.app_env == "production":
            origins = [v.strip() for v in self.allowed_origins.split(",")]
            if not self.auth_cookie_secure or not origins or any(not v.startswith("https://") or "*" in v for v in origins):
                raise ValueError("Production requires secure cookies and explicit HTTPS origins.")
            if self.auth_demo_enabled:
                raise ValueError("Demo authentication cannot be enabled in production.")
        return self


settings = Settings()
