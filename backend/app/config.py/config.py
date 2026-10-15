"""Backend configuration.

All secrets come from environment. No defaults that look like real credentials.
SUPABASE_SERVICE_ROLE_KEY / SUPABASE_DB_URL are server-side only — this module
is never imported by frontend code.
"""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    # Server-side only:
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_DB_URL: str = ""
    FASTAPI_BASE_URL: str = "http://localhost:8000"
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    INGESTION_SECRET: str = ""
    SENTRY_DSN: str = ""
    LOG_LEVEL: str = "INFO"
    INGESTION_PAGE_DELAY_SECONDS: float = 1.5
    INGESTION_MAX_PAGES: int = 50
    INGESTION_TIMEOUT_SECONDS: float = 30.0

    @property
    def has_supabase(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_ROLE_KEY)

    @property
    def has_db_url(self) -> bool:
        return bool(self.SUPABASE_DB_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def require_ingestion_secret(provided: str | None, settings: Settings | None = None) -> bool:
    """Constant-time-ish comparison for the ingestion secret. Empty secret = deny."""
    import hmac

    s = settings or get_settings()
    if not s.INGESTION_SECRET or not provided:
        return False
    return hmac.compare_digest(provided, s.INGESTION_SECRET)
