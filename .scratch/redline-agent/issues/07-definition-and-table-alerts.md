# Get warned about definition and table changes

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Surface two high-value structural alerts in the feed. When a defined term's definition changes, raise a prominent alert noting how many clauses reference that term ("definition of X changed — affects N clauses"). When a table (e.g. a pricing schedule) changes, raise a "table modified — review manually" alert instead of attempting a cell-level diff.

## Acceptance criteria

- [ ] A changed defined-term definition is detected and flagged with a reference/affected-clause count
- [ ] A changed table is detected and surfaced as a manual-review alert (no cell-level diff)
- [ ] Both alerts render prominently in the change feed
- [ ] Tests written first: defined-term detection and reference counting on fixtures; table-change detection; feed alert rendering against mocked API

## Blocked by

- `.scratch/redline-agent/issues/03-plain-english-change-summaries.md`
