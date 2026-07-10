"""Application settings.

The database URL defaults to a local SQLite file so the service runs without a
Postgres server. In deployment it is pointed at Postgres via ``REDLINE_DB_URL``;
the ORM and repositories are engine-agnostic.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDLINE_", env_file=".env")

    # async SQLAlchemy URL; swap for postgresql+asyncpg://... in deployment.
    db_url: str = "sqlite+aiosqlite:///./redline_agent.db"
    # single-tenant operation in v1 (decision #8); schema is tenant-ready.
    default_tenant_id: str = "default"


def get_settings() -> Settings:
    return Settings()
