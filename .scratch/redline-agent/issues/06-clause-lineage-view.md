# Trace how a clause evolved

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Let the user click any clause and see its full cross-round lineage — how that clause's text changed across every round of the negotiation. This is the payoff of the stateful tracker.

## Acceptance criteria

- [x] `GET /clauses/{id}/lineage` returns the clause's text and change across all rounds in order
- [x] React drill-down component renders the cross-round evolution from a change in the feed
- [x] Lineage follows human alignment overrides where present
- [x] Tests written first: lineage query against real Postgres (including an overridden link); React lineage component against mocked API

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`

## Comments

- 2026-07-11 (agent): Claiming this issue. Implementing `GET /clauses/{id}/lineage`
  backend endpoint + React drill-down lineage component, following overrides.
- 2026-07-11 (agent): Done. Vertical slice end to end:
  - **Backend**: `ChangeQueryService.clause_lineage` walks the persisted
    `ClauseLineage` links backward and forward from a clause to assemble its
    cross-round chain (round order), each entry carrying the round, clause text,
    and the `Change` into it. New repo methods `ClauseLineageRepository.get_by_prev_clause`
    (forward step) and `ChangeRepository.get_by_curr_clause`. New `clauses` router
    exposes `GET /clauses/{id}/lineage` (`ClauseLineageOut` / `LineageEntryOut`
    DTOs), registered in `main.py`. Because the walk follows stored links —
    which an override rewrites — lineage follows human corrections (decision #5)
    for free.
  - **Frontend**: `getClauseLineage` client fn + `ClauseLineage`/`LineageEntry`
    types; `ClauseLineage` drill-down component rendering the round timeline;
    wired into `ChangeCard` behind a "Show clause history" toggle (lineage is
    only fetched when opened).
  - **Tests (written first)**: `tests/services/test_clause_lineage.py` (real DB,
    3-round trace + an overridden-link case that severs the chain + unknown
    clause → None); two API tests in `test_api.py`; `ClauseLineage.test.tsx` +
    a drill-down test in `ChangeCard.test.tsx` (MSW-mocked API).
  - Full suites green: backend 84 passed, frontend 20 passed, `tsc --noEmit` clean.
  - Note on scope: a clause split (several current clauses → one prior) makes the
    forward walk ambiguous; it takes the first link (primary chain). Left as-is
    for this slice; documented on `get_by_prev_clause`.
