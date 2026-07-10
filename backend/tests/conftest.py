"""Shared test fixtures.

Each test gets a fresh in-memory SQLite database (StaticPool so all sessions
share the one connection) with the full schema created. This stands in for the
per-test-transaction Postgres described in ARCHITECTURE.md; the repositories are
engine-agnostic.
"""

from __future__ import annotations

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from redline_agent.infra.blob_store import InMemoryBlobStore
from redline_agent.infra.llm.interpreter import FakeInterpreter
from redline_agent.repositories.orm import Base

TENANT = "test-tenant"


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
def blob_store():
    return InMemoryBlobStore()


@pytest_asyncio.fixture
def interpreter():
    """A deterministic, offline interpreter for orchestration tests."""
    return FakeInterpreter(summary="Machine-generated summary.")
