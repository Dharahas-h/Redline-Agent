# Get warned about definition and table changes

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Surface two high-value structural alerts in the feed. When a defined term's definition changes, raise a prominent alert noting how many clauses reference that term ("definition of X changed — affects N clauses"). When a table (e.g. a pricing schedule) changes, raise a "table modified — review manually" alert instead of attempting a cell-level diff.

## Acceptance criteria

- [x] A changed defined-term definition is detected and flagged with a reference/affected-clause count
- [x] A changed table is detected and surfaced as a manual-review alert (no cell-level diff)
- [x] Both alerts render prominently in the change feed
- [x] Tests written first: defined-term detection and reference counting on fixtures; table-change detection; feed alert rendering against mocked API

## Blocked by

- `.scratch/redline-agent/issues/03-plain-english-change-summaries.md`

## Comments

- 2026-07-11 (agent): Claiming this issue. Implementing defined-term
  definition-change detection with reference/affected-clause count and
  table-change detection (manual-review alert, no cell-level diff), surfaced
  prominently in the change feed.
- 2026-07-11 (agent): Done. Vertical slice end to end, alerts modeled as a
  separate `StructuralAlert` concept so the deterministic differ stays the sole
  authority on the change set (decision #1) and the ripple/table flags never
  become fabricated changes.
  - **Detection (pure pipeline)**: new `pipeline/defined_terms.py`
    (`extract_definitions`, `count_references`, `detect_definition_changes`) —
    parses `"Term" means …` / `shall mean` (straight & curly quotes), reports
    only terms defined in *both* rounds whose definition text differs, and
    counts referencing clauses excluding the defining clause. New
    `pipeline/tables.py` (`extract_table_signatures`, `detect_table_changes`) —
    tables are dropped from canonical text (decision #6), so a per-table
    flattened cell signature is compared positionally (added/removed/modified),
    never cell-diffed.
  - **Persistence**: `AlertType` enum + `StructuralAlert` model; `RoundRow`
    gains `table_signatures` (JSON) and a new `structural_alerts` table
    (`StructuralAlertRow` + `StructuralAlertRepository`); migration
    `0003_structural_alerts`. Signatures are computed at upload
    (`create_round`, where docx bytes are in hand) alongside canonical text.
  - **Orchestration**: `RoundService._regenerate_alerts` rebuilds alerts from
    the diffed pairs after changes are persisted; cleared-then-recreated so an
    alignment override regenerates them idempotently (no duplication).
  - **Query/API**: `ChangeQueryService.structural_alerts`; `StructuralAlertOut`
    DTO; `RoundChangesOut.alerts` populated in the feed payload (so both feed
    and override responses carry them).
  - **Frontend**: `StructuralAlert`/`AlertType` types + `alerts` on
    `RoundChanges`; new `StructuralAlerts` banner rendered above the change
    cards in `ChangeFeed` (guarded `?? []` for older mock payloads).
  - **Tests (written first)**: `tests/pipeline/test_defined_terms.py`,
    `tests/pipeline/test_tables.py` (fixtures via extended `docx_builder`
    table support); `tests/services/test_structural_alerts.py` (real DB — incl.
    a table-only edit that yields *zero* changes but one alert, override
    regeneration, tenant isolation); two API tests in `test_api.py`;
    `StructuralAlerts.test.tsx` + a feed-banner test in `ChangeFeed.test.tsx`
    (MSW). Full suites green: backend 106 passed, frontend 25 passed,
    `tsc --noEmit` clean.
  - Scope notes: definition matching is quote+"means" heuristic and
    first-definition-wins; table matching is positional (a reordered table reads
    as removed+added — a safe review prompt), matching the export's decision #4
    tradeoff. Feature `redline-agent` still has issue 08 (HITL) open, so it
    stays in the backlog.
