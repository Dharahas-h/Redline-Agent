"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from redline_agent.api.routers import changes, negotiations
from redline_agent.config import Settings, get_settings
from redline_agent.infra.blob_store import BlobStore, InMemoryBlobStore
from redline_agent.repositories.db import (
    create_schema,
    make_engine,
    make_session_factory,
)


def create_app(
    settings: Settings | None = None,
    blob_store: BlobStore | None = None,
    engine=None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine if engine is not None else make_engine(settings.db_url)
    session_factory = make_session_factory(engine)
    blob_store = blob_store or InMemoryBlobStore()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await create_schema(engine)
        yield
        await engine.dispose()

    app = FastAPI(title="Redline Agent", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.blob_store = blob_store

    app.include_router(negotiations.router)
    app.include_router(changes.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
