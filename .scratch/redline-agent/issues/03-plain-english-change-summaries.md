# Understand each change in plain English

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Deepen the change feed so each changed clause carries a plain-English summary of what changed and a materiality tag (substantive vs cosmetic), and the user can filter cosmetic noise out.

Introduces the Interpreter stage behind a swappable `LLMInterpreter` Protocol, invoked per change, concurrently, with caching, and only on material changes. The deterministic diff remains the source of truth for *what* changed; interpretation only explains it. The raw before/after stays visible behind every summary.

## Acceptance criteria

- [ ] Each change in the feed shows a plain-English summary and a materiality tag
- [ ] The feed can be filtered by materiality (hide cosmetic)
- [ ] Interpretation runs per-change, concurrently, cached, and skips non-material changes
- [ ] `LLMInterpreter` is a Protocol with a real Azure OpenAI implementation and a test fake
- [ ] Raw before/after remains accessible for every change; interpretation is labeled machine-generated
- [ ] Invariant preserved: with a garbage-returning `FakeInterpreter`, the set of changes is unchanged
- [ ] Tests written first: interpreter stage with `FakeInterpreter`; feed API filter behavior; React badge/filter components against mocked API

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`
