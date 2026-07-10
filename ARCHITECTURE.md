# Architecture

## Overview

The Redline Agent is a deterministic pipeline (no autonomous agent loop) that
ingests each `.docx` round of a negotiation, computes what changed versus the
prior round, interprets each change with an LLM, and tracks how every clause
evolves. A React SPA presents a clause-centric change feed; a standalone export
produces a tracked-changes `.docx`.

Core principle: the deterministic diff decides WHAT changed; the LLM only
explains what it MEANS. The model never invents or detects changes.

## Component map

```
React + TS SPA  ──REST/JSON──▶  FastAPI (api layer)
                                     │
                                Application services
                    ┌────────────────┴───────────────┐
              Pipeline (deterministic)         redline (STANDALONE
        Ingestor → Segmenter → Aligner →       export package —
        Differ → Interpreter                   no pipeline imports)
                    │                                 │
        Repositories        Embedder / LLMInterpreter │
                    │        / BlobStore (Protocols)   │
              Postgres + Azure Blob ◀──────────────────┘
```

## Layering rule (inward-only)

`api → services → pipeline/domain → repositories → infra`

Dependencies point inward only; nothing points back out. The `redline` export
package sits OUTSIDE this graph — it imports nothing from `pipeline`/`domain`
and is a pure function `redline(prev_docx, curr_docx) -> docx`.

## Backend folder structure

```
backend/src/redline_agent/
├── main.py            # FastAPI app factory
├── config.py          # settings (DB, blob, LLM keys)
├── deps.py            # FastAPI dependency providers
├── api/
│   ├── routers/       # negotiations, rounds, changes, clauses, export
│   └── schemas/       # pydantic request/response DTOs
├── services/          # negotiation, round (orchestrates pipeline), change_query, export
├── pipeline/          # ingestor, flatten, segmenter, aligner, differ, interpreter, defined_terms
├── redline/           # STANDALONE: paragraph_align, word_diff, ooxml_writer
├── domain/            # pure models + enums, no I/O
├── repositories/      # orm + per-entity repos
└── infra/             # blob_store, embedder, llm/ (Protocols + impls)
```

## Frontend folder structure

```
frontend/src/
├── api/          # typed client, one fn per route
├── pages/        # NegotiationList, NegotiationDetail, RoundReview (signature view)
├── components/   # ChangeFeed, ChangeCard, ClauseLineage, AlignmentOverride, ExportButton
└── types/        # mirror backend DTOs
```

The signature view is the clause-centric interpreted change feed with
drill-through to a clause's cross-round lineage — not a side-by-side diff.

## Data model (Postgres, tenant-ready from migration #1)

- `negotiations` (id, tenant_id, title, represented_party, created_at)
- `rounds` (id, negotiation_id, round_no, submitted_by_party, blob_uri,
  canonical_text, status, created_at) — full snapshot per round; diffs derived
- `clauses` (id, round_id, ordinal, number_label, heading, text, embedding)
- `clause_lineage` (id, negotiation_id, prev_clause_id, curr_clause_id,
  similarity, confidence, align_method, overridden)
- `changes` (id, negotiation_id, from_round_id, to_round_id, curr_clause_id,
  change_type, raw_before, raw_after, summary, materiality, category,
  favored_party, risk_flag, interpretation_model) — interpretation nullable

Raw `.docx` files are stored in Azure Blob and referenced by `rounds.blob_uri`.

## API routes

| Method | Route | Purpose |
|---|---|---|
| POST | /negotiations | Create matter (title, represented_party) |
| GET | /negotiations | List |
| GET | /negotiations/{id} | Detail + rounds summary |
| POST | /negotiations/{id}/rounds | Upload .docx → runs pipeline (background) |
| GET | /negotiations/{id}/rounds | List rounds |
| GET | /rounds/{id}/changes | Clause-centric feed (filters + status) |
| GET | /changes/{id} | Single change + raw before/after |
| GET | /clauses/{id}/lineage | Cross-round evolution |
| PATCH | /rounds/{id}/alignment | Human override → regenerates diff |
| POST | /negotiations/{id}/export | Latest-vs-prior tracked-changes .docx |
| GET | /exports/{id} | Download |

Uploads run the pipeline as a background task with round `status` polling
(in-process for v1; a task queue is a later swap).

## Test seams (highest available)

- **Protocol seams** — `Embedder`, `LLMInterpreter`, `BlobStore` injected as
  fakes (`FakeEmbedder` returns deterministic vectors keyed on text;
  `FakeInterpreter` returns canned structured output; `InMemoryBlobStore`).
  No pipeline or service test hits the network.
- **`RoundService` orchestration seam** — highest-value integration test: feed a
  `.docx` fixture with fakes injected and real Postgres (transaction rolled back
  per test), assert persisted Clauses/Changes and the returned feed.
- **API seam** — `httpx.AsyncClient` behavioral tests per route.
- **`redline()` public-function seam** — golden-file `.docx` tests, independent
  of the pipeline.
- **Frontend API boundary** — Vitest + React Testing Library + MSW.

Core invariant as a test: with a garbage-returning `FakeInterpreter`, the set of
`Change` rows must equal exactly what the deterministic Differ produced.

Tooling: `pytest` + `pytest-asyncio`, `httpx.AsyncClient`, golden `.docx`
fixtures, `factory-boy`; Vitest + RTL + MSW on the frontend. CI coverage is a
floor, not a target.
