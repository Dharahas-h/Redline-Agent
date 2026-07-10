# Skeleton: upload two rounds, see what changed

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

The end-to-end spine of the Redline Agent at its simplest. A user creates a negotiation (declaring which party they represent), uploads two `.docx` rounds, and sees a clause-centric feed of the clauses that changed between the two rounds, each showing its raw before/after text.

This is the walking skeleton: it must touch every architectural tier once — the full Postgres schema (all tables, tenant-ready from the first migration), `.docx` ingestion (flatten to canonical normalized text, store the original file in Azure Blob by reference, persist a per-round snapshot), structure-based clause segmentation, **trivial positional clause alignment** (match by ordinal/number — no embeddings yet), word-level diff of aligned clauses, the background-task + round-`status` mechanism, the changes feed API, and the React feed UI. Depth is intentionally shallow at each tier; later slices deepen specific journeys.

Core invariant to establish here: the set of detected changes is exactly what the deterministic differ produces — nothing invents changes.

## Acceptance criteria

- [ ] `POST /negotiations` creates a negotiation with a title and `represented_party`; `GET` lists and fetches them
- [ ] `POST /negotiations/{id}/rounds` accepts a `.docx` upload, stores the original blob, flattens to canonical text, persists a round snapshot with `round_no` and `submitted_by_party`, and runs the pipeline as a background task
- [ ] Round exposes a `status` that transitions (e.g. pending → ready) and is pollable
- [ ] Uploading a second round segments both rounds into clauses, aligns them positionally, and persists detected changes with raw before/after
- [ ] `GET /rounds/{id}/changes` returns the clause-centric feed of changed clauses
- [ ] React app can create a negotiation, upload two rounds, and render the change feed with before/after text
- [ ] Schema includes `tenant_id` on the appropriate tables from migration #1
- [ ] Tests written first: pipeline stages (flatten, segmenter, differ) against fixtures; `RoundService` orchestration against real Postgres with `InMemoryBlobStore`; API routes via async client; the "changes == differ output" invariant test; React feed component against mocked API

## Blocked by

None - can start immediately
