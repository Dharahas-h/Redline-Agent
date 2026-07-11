# Segment non-decimal clause enumerations

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/enhancements/PRD.md`

## Context

The segmenter (`backend/src/redline_agent/pipeline/segmenter.py`) currently
recognizes only three clause-start patterns: multi-level decimal (`1.1`,
`2.3.4`), a single integer with a `.`/`)` separator (`1.`, `2)`), and all-caps
heading lines. Contracts whose *primary* structure uses alphabetic, roman, or
parenthetical enumeration are not segmented: the whole document collapses into a
single oversized clause (or preamble). This silently degrades diff granularity
and breaks **clause lineage** — the PRD calls the segmentation/alignment layer
the backbone the whole pipeline leans on.

This is an implementation gap in one stage, not a design change: the
`redline-agent` PRD says "structure-based clause segmentation from
heading/numbering" without committing to decimal-only, and nothing downstream
assumes decimal numbering (alignment is embedding-similarity based; clause
numbers are only a hint).

## What to build

Extend `_match_start` to recognize additional clause-start enumerations as
first-class clause boundaries, producing a `number_label` the same way the
existing patterns do:

- Alphabetic — `a.`, `b)`, `(a)`
- Roman — `i.`, `ii.`, `iv)` (lowercase and uppercase)
- Parenthetical numeric — `(1)`, `(2)`

Nested sub-enumerations that sit under a recognized parent (e.g. `a.`/`b.`
beneath `1.`) should continue to fold into their parent clause's body as they do
today — the goal is to recognize these patterns when they carry the document's
*primary* structure, not to over-segment every inline list. Keep the existing
guard that bare prose (e.g. "30 days notice") is never mistaken for a clause
number.

## Acceptance criteria

- [ ] A document whose sections are lettered (`(a)`, `(b)`, ...) segments into
      one clause per section, with the letter captured as `number_label`
- [ ] A document whose sections use roman numerals (`I.`/`II.` or `i.`/`ii.`)
      segments per section with the numeral as `number_label`
- [ ] A document using parenthetical numeric (`(1)`, `(2)`) segments per section
- [ ] Existing decimal, single-integer, all-caps, and preamble behavior is
      unchanged (existing tests still pass)
- [ ] Bare prose containing numbers/letters is not mis-segmented (regression
      guard retained)
- [ ] Tests written first: one case per new enumeration style plus a
      mixed-structure document, alongside the existing segmenter tests

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md`

## Comments

- 2026-07-11: Filed after a design discussion surfaced that the segmenter is
  decimal-and-all-caps-biased. `test_segmenter.py` currently has no coverage for
  alphabetic/roman/parenthetical input, so the gap was silent. Degrades
  gracefully (coarser clauses, no crash) but hurts diff noise and lineage.
