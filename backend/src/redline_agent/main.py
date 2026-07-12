"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from redline_agent.api.routers import changes, clauses, export, negotiations
from redline_agent.config import Settings, get_settings
from redline_agent.infra.blob_store import BlobStore, build_blob_store
from redline_agent.infra.embedder import Embedder, build_embedder
from redline_agent.infra.llm import LLMInterpreter, build_interpreter
from redline_agent.infra.llm.adjudicator import (
    AlignmentAdjudicator,
    build_adjudicator,
)
from redline_agent.repositories.db import (
    create_schema,
    make_engine,
    make_session_factory,
)


def create_app(
    settings: Settings | None = None,
    blob_store: BlobStore | None = None,
    engine=None,
    interpreter: LLMInterpreter | None = None,
    embedder: Embedder | None = None,
    adjudicator: AlignmentAdjudicator | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    engine = engine if engine is not None else make_engine(settings.db_url)
    session_factory = make_session_factory(engine)
    blob_store = blob_store or build_blob_store(settings)
    interpreter = interpreter or build_interpreter(settings)
    embedder = embedder or build_embedder(settings)
    adjudicator = adjudicator or build_adjudicator(settings)

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
    app.state.interpreter = interpreter
    app.state.embedder = embedder
    app.state.adjudicator = adjudicator

    app.include_router(negotiations.router)
    app.include_router(changes.router)
    app.include_router(clauses.router)
    app.include_router(export.router)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
