"""Application settings.

The database URL defaults to a local SQLite file so the service runs without a
Postgres server. In deployment it is pointed at Postgres via ``REDLINE_DB_URL``;
the ORM and repositories are engine-agnostic.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Anchor to this file's directory so the .env is found regardless of the
        # process working directory (uvicorn is usually launched from backend/).
        env_file=Path(__file__).parent / ".env", extra="ignore"
    )

    # async SQLAlchemy URL; swap for postgresql+asyncpg://... in deployment.
    db_url: str = "sqlite+aiosqlite:///./redline_agent.db"
    # single-tenant operation in v1 (decision #8); schema is tenant-ready.
    default_tenant_id: str = "default"

    # Chat interpreter + alignment adjudicator (decision #7). An OpenAI-compatible
    # client: leave ``openai_base_url`` unset for api.openai.com, or point it at
    # an Azure AI Foundry ``/openai/v1/`` endpoint. When key + model are set the
    # real interpreter/adjudicator are used; otherwise the offline fakes stand in.
    # Bare ``OPENAI_*`` names are accepted alongside the ``REDLINE_`` prefix.
    openai_api_key: str | None = Field(
        default=None,
        alias="OPENAI_API_KEY"
    )
    openai_base_url: str | None = Field(
        default=None,
        alias="OPENAI_BASE_URL"
    )
    openai_model: str | None = Field(
        default=None,
        alias="OPENAI_MODEL"
    )

    # Embeddings for clause alignment (decision #7). Same OpenAI-compatible shape;
    # when key + model are set the real embedder is used, else the offline fake.
    embedding_api_key: str | None = Field(
        default=None,
        alias="EMBEDDING_API_KEY"
    )
    embedding_base_url: str | None = Field(
        default=None,
        alias="EMBEDDING_BASE_URL"
    )
    embedding_model: str | None = Field(
        default=None,
        alias="EMBEDDING_MODEL"
    )

    # Connection to Azure Blob Storage for .docx round files. When set, the real
    # blob store is used; else the in-memory store is used for tests and local dev
    blob_connection_string: str | None = Field(
        default=None,
        alias="BLOB_CONNECTION_STRING"
    )


def get_settings() -> Settings:
    return Settings()
