# Fix a wrong match

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Let the user correct clause alignment when the automatic match is wrong, and make the automatic matching good enough to flag its own uncertainty. The feed marks low-confidence clause matches; the user can re-pair, split, or merge clauses; the diff (and any interpretation) regenerates from the correction.

This slice replaces Slice 1's trivial positional alignment with embedding-similarity alignment (via a swappable `Embedder` Protocol) plus clause-number/heading matching, records a confidence and alignment method on each lineage link, and invokes the LLM only to adjudicate genuinely ambiguous splits/merges/moves. The smarter aligner exists to serve the correction journey.

## Acceptance criteria

- [ ] Clause alignment uses embedding similarity + number/heading match; ambiguous cases fall back to the LLM adjudicator
- [ ] Each lineage link records similarity, confidence, alignment method, and an `overridden` flag
- [ ] Low-confidence matches are visually flagged in the feed
- [ ] `PATCH /rounds/{id}/alignment` lets the user re-pair/split/merge; the diff and interpretation regenerate
- [ ] `Embedder` is a Protocol with an Azure implementation and a deterministic test fake
- [ ] Tests written first: aligner with `FakeEmbedder` including low-confidence and LLM-fallback cases; override → regeneration behavior via API; React override component

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`
