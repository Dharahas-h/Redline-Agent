# Trace how a clause evolved

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Let the user click any clause and see its full cross-round lineage — how that clause's text changed across every round of the negotiation. This is the payoff of the stateful tracker.

## Acceptance criteria

- [ ] `GET /clauses/{id}/lineage` returns the clause's text and change across all rounds in order
- [ ] React drill-down component renders the cross-round evolution from a change in the feed
- [ ] Lineage follows human alignment overrides where present
- [ ] Tests written first: lineage query against real Postgres (including an overridden link); React lineage component against mocked API

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`
