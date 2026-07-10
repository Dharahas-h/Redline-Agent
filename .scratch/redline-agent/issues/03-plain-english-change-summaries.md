# Understand each change in plain English

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Deepen the change feed so each changed clause carries a plain-English summary of what changed and a materiality tag (substantive vs cosmetic), and the user can filter cosmetic noise out.

Introduces the Interpreter stage behind a swappable `LLMInterpreter` Protocol, invoked per change, concurrently, with caching, and only on material changes. The deterministic diff remains the source of truth for *what* changed; interpretation only explains it. The raw before/after stays visible behind every summary.

## Acceptance criteria

- [x] Each change in the feed shows a plain-English summary and a materiality tag
- [x] The feed can be filtered by materiality (hide cosmetic)
- [x] Interpretation runs per-change, concurrently, cached, and skips non-material changes
- [x] `LLMInterpreter` is a Protocol with a real Azure OpenAI implementation and a test fake
- [x] Raw before/after remains accessible for every change; interpretation is labeled machine-generated
- [x] Invariant preserved: with a garbage-returning `FakeInterpreter`, the set of changes is unchanged
- [x] Tests written first: interpreter stage with `FakeInterpreter`; feed API filter behavior; React badge/filter components against mocked API

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`

## Comments

- 2026-07-11 (agent): Claiming this issue. Issue 01 (skeleton) is complete, so
  changes with raw before/after are already persisted per round. Building the
  Interpreter stage behind an `LLMInterpreter` Protocol (`infra/llm/`): a
  deterministic cosmetic pre-filter skips non-material (whitespace-only) changes
  without an LLM call, material candidates are interpreted per-change,
  concurrently, deduped/cached by content; the stage fills `summary` +
  `materiality` only (favored-party/category/risk are issue 04). Wiring it into
  `RoundService` after the differ (never altering the change set — decision #1),
  extending the invariant test with a garbage `FakeInterpreter`, the feed
  materiality filter (already scaffolded in `ChangeQueryService`), and the React
  summary/materiality badge + hide-cosmetic filter. Tests written first.

- 2026-07-11 (agent): Completed. All acceptance criteria met; tests written
  first and passing (48 backend, 7 frontend; `tsc -b` + `vite build` clean).
  - **`LLMInterpreter` Protocol** (`infra/llm/`): `interpreter.py` defines the
    `LLMInterpreter` Protocol, `InterpretationRequest`/`Interpretation`
    dataclasses (summary + materiality only this slice), and the deterministic
    offline `FakeInterpreter` (counts calls; canned or per-change default
    summary). `azure_openai.py` is the real default impl (decision #7) — lazy
    `openai` import so the module loads without the package or credentials;
    never exercised by tests. `__init__.build_interpreter(settings)` picks Azure
    when configured, else falls back to `FakeInterpreter` so the app runs
    offline (same environment-convenience posture as the SQLite fallback).
  - **Interpreter stage** (`pipeline/interpreter.py`): `interpret_changes` fills
    `summary`/`materiality`/`interpretation_model` on changes *in place* and
    never alters the set (decision #1). A cheap deterministic pre-filter tags
    case/punctuation/whitespace-only modifications as cosmetic and skips the
    LLM; material candidates (incl. all added/removed) are deduped by content
    (one call per unique before/after — caching) and interpreted concurrently
    via `asyncio.gather`.
  - **Wiring**: `RoundService` takes an injected `LLMInterpreter` and runs the
    stage between the differ and persistence; `deps`/`main`/`config` provide it
    from `app.state` (new optional `azure_openai_*` settings). The feed's
    materiality filter was already scaffolded in `ChangeQueryService`, so
    `?materiality=substantive` now hides cosmetic changes.
  - **Frontend**: `ChangeCard` shows a materiality badge and the plain-English
    summary labeled "Machine-generated — attorney work-product for review", with
    raw before/after still shown behind it; `ChangeFeed` has a "Hide cosmetic
    changes" checkbox that re-queries the feed server-side; `getRoundChanges`
    gained an optional `materiality` arg.
  - **Invariant**: the changes-==-differ test now drives the pipeline with a
    garbage-returning `FakeInterpreter` (nonsense summary, wrong materiality)
    and still asserts the persisted change set equals the differ's output.
  - **Deviations / notes:**
    - No DB migration needed — interpretation columns already exist (nullable)
      from migration `0001`.
    - "Cosmetic" is defined this slice as case/punctuation/whitespace-only
      (flatten already collapses whitespace, so a pure-whitespace delta never
      reaches the differ); anything else is a material candidate. Favored-party,
      category, and risk are deliberately left for issue 04.
