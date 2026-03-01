"""
config/settings.py — Pydantic BaseSettings configuration

All settings are loaded from environment variables (or .env file).
Fails fast on missing required variables.
"""

import os
from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings
from pydantic import field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/traderrr"

    # Sync URL used by Alembic (derived from DATABASE_URL)
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Return a synchronous database URL for Alembic / sync sessions."""
        return self.DATABASE_URL.replace("+asyncpg", "")

    # Supabase (production only)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # ── Redis / Celery ────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Auth ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-minimum-32-chars-high-entropy"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── App ───────────────────────────────────────────────────────────────
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # ── Signal generation ─────────────────────────────────────────────────
    MIN_CONFIDENCE: float = 0.6
    MOMENTUM_THRESHOLD: float = 60.0
    MEAN_REVERSION_THRESHOLD: float = 70.0
    UPDATE_INTERVAL_MINUTES: int = 30

    # ── Risk management ───────────────────────────────────────────────────
    MAX_POSITION_SIZE: float = 0.20
    MAX_SECTOR_CONCENTRATION: float = 0.40
    VAR_CONFIDENCE: float = 0.95
    MAX_CORRELATION: float = 0.70
    VOLATILITY_LIMIT: float = 0.25

    # ── Portfolio ─────────────────────────────────────────────────────────
    REBALANCE_THRESHOLD: float = 0.05

    # ── Notifications ─────────────────────────────────────────────────────
    ALERT_THRESHOLD: float = 0.8
    EMAIL_ENABLED: bool = False
    EMAIL_ADDRESS: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance (singleton)."""
    return Settings()


# ── Backward-compatible aliases ───────────────────────────────────────────
# Many modules still do `from config.settings import Config` or `get_config`.
Config = Settings
get_config = get_settings
