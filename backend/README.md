# Redline Agent — backend

FastAPI service implementing the deterministic pipeline (ingest → segment →
align → diff) and the clause-centric change feed. See `../ARCHITECTURE.md`.

## Setup

```bash
python -m venv ../.venv && . ../.venv/bin/activate
pip install -e '.[dev]'
```

## Database

The DB engine is configured via `REDLINE_DB_URL` (SQLAlchemy async URL). It
defaults to a local SQLite file so the service runs with no external
dependency; point it at Postgres in deployment:

```bash
export REDLINE_DB_URL="postgresql+asyncpg://user:pass@host/redline"
```

> **Environment note:** this repo's dev/test environment has no Postgres, so
> SQLite backs local runs and tests. The ORM and repositories are
> engine-agnostic; the schema is Postgres-portable and tenant-ready from
> migration #1.

Apply migrations (canonical schema, `tenant_id` on every table):

```bash
alembic upgrade head
```

The app also creates the schema from ORM metadata on startup for convenience.

## Run

```bash
uvicorn redline_agent.main:app --reload
```

## Test

```bash
pytest
```

Tests use in-memory SQLite, `InMemoryBlobStore`, and no network. Key seams:
pipeline stages (`tests/pipeline`), `RoundService` orchestration and the
"changes == differ output" invariant (`tests/services`), and API routes
(`tests/api`).
