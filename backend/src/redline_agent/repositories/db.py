"""Async engine, session factory, and schema bootstrap.

Schema is created from the ORM metadata (``create_all``). The canonical DDL
also lives as Alembic migration #1 for the Postgres deployment path; both are
kept in sync with ``orm.py``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from redline_agent.repositories.orm import Base


def make_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(db_url, future=True)


def make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    async with factory() as session:
        yield session
