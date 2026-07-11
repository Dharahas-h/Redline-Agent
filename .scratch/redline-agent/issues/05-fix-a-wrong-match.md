# Fix a wrong match

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Let the user correct clause alignment when the automatic match is wrong, and make the automatic matching good enough to flag its own uncertainty. The feed marks low-confidence clause matches; the user can re-pair, split, or merge clauses; the diff (and any interpretation) regenerates from the correction.

This slice replaces Slice 1's trivial positional alignment with embedding-similarity alignment (via a swappable `Embedder` Protocol) plus clause-number/heading matching, records a confidence and alignment method on each lineage link, and invokes the LLM only to adjudicate genuinely ambiguous splits/merges/moves. The smarter aligner exists to serve the correction journey.

## Acceptance criteria

- [x] Clause alignment uses embedding similarity + number/heading match; ambiguous cases fall back to the LLM adjudicator
- [x] Each lineage link records similarity, confidence, alignment method, and an `overridden` flag
- [x] Low-confidence matches are visually flagged in the feed
- [x] `PATCH /rounds/{id}/alignment` lets the user re-pair/split/merge; the diff and interpretation regenerate
- [x] `Embedder` is a Protocol with an Azure implementation and a deterministic test fake
- [x] Tests written first: aligner with `FakeEmbedder` including low-confidence and LLM-fallback cases; override → regeneration behavior via API; React override component

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`

## Comments

- 2026-07-11 — Claude (agent): Claiming this issue. Blocker (issue 01) is
  complete. Implementing embedding-similarity + number/heading alignment behind
  an `Embedder` Protocol, LLM adjudication for ambiguous cases, confidence on
  lineage links, low-confidence flagging in the feed, and the
  `PATCH /rounds/{id}/alignment` override → regeneration path.
- 2026-07-11 — Claude (agent): Done. All acceptance criteria met; 79 backend
  tests + 16 frontend tests pass, frontend `tsc -b` clean.

  **Backend**
  - `infra/embedder.py`: `Embedder` Protocol + `AzureEmbedder`
    (`text-embedding-3-large`, lazy `openai` import) + deterministic
    `FakeEmbedder` (batch-shared bag-of-words vocabulary → cosine = lexical
    overlap, collision-free) + `build_embedder`.
  - `infra/llm/adjudicator.py`: `AlignmentAdjudicator` Protocol +
    `AzureOpenAIAdjudicator` + `FakeAdjudicator` + `build_adjudicator` (returns
    `None` offline, so ambiguous matches are flagged rather than decided by a
    stand-in — decision #5).
  - `pipeline/aligner.py`: new async `align()` — structural (number/heading,
    full confidence) → embedding cosine (confident when clearly-best &
    high-sim) → LLM adjudication for ambiguous cases; falls back to a flagged
    best-guess when no adjudicator. Records `similarity`/`confidence`/method per
    pair; `is_low_confidence()` helper. `align_positional()` retained as the
    no-embedder fallback (existing tests unchanged).
  - `RoundService`: injects `embedder`/`adjudicator` (optional — positional
    fallback when absent), persists confidence/method on lineage, and adds
    `override_alignment()` (re-pair/split/merge via a `links` list) that marks
    lineage `overridden`/`override` and regenerates diff+interpretation via a
    shared `_regenerate_changes()` (clears the round's changes first, so it is
    idempotent; differ stays the sole authority — decision #1).
  - Repos: `ClauseLineageRepository.list_for_round/get_by_curr_clause/update`;
    `ChangeRepository.delete_for_round`. No migration needed — lineage columns
    existed since migration #1.
  - API: `PATCH /rounds/{id}/alignment` returns the regenerated feed;
    `ChangeOut` now carries `alignment_confidence/method/similarity`,
    `low_confidence`, `overridden` (joined from lineage in the feed and the
    single-change endpoint).

  **Frontend**
  - `AlignmentOverride` component (re-pair to a prior clause or mark-as-new;
    candidates derived from the feed, no extra endpoint), wired into
    `ChangeCard`/`ChangeFeed`; low-confidence and corrected-match badges;
    `updateAlignment` client fn; types extended.

  **Decisions / deviations**
  - Split/merge are expressed through the same `links` array (a merge points
    several current clauses at one prior; a split leaves extras as additions).
    The UI exposes re-pair + mark-as-new; a dedicated clause-picker endpoint was
    deliberately not added to avoid pulling scope from later issues — candidates
    are derived client-side from the feed.
  - Offline/default (no Azure) now uses `FakeEmbedder` for alignment, mirroring
    the existing `FakeInterpreter`/SQLite fallbacks — an environment
    convenience, not a scope change. Labeled clauses match structurally first,
    so issue 01–04 behaviour and tests are unchanged.
