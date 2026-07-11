# See what each change costs me

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Turn the feed into a negotiation tool: each change shows whether it favors the party the user represents or the counterparty, a category tag (payment, liability, IP, termination, confidentiality, etc.), and an attorney-review risk flag. The user can filter by favored-party, category, and risk.

Extends the Interpreter's structured output to include favored-party (computed relative to the negotiation's `represented_party` captured in Slice 1), category, and a risk flag framed as a prompt for attorney review — never a legal conclusion.

## Acceptance criteria

- [x] Each change shows a favored-party badge (favors me / favors them) derived from `represented_party`
- [x] Each change shows a category tag and an attorney-review risk flag
- [x] The feed can be filtered by favored-party, category, and risk
- [x] Risk output is phrased as a review prompt, and all output is framed as attorney work-product
- [x] Tests written first: interpreter output schema with `FakeInterpreter`; favored-party correctness relative to `represented_party`; feed filter behavior; React badge/filter components

## Blocked by

- `.scratch/redline-agent/issues/03-plain-english-change-summaries.md`

## Comments

- 2026-07-11 (agent): Claiming this issue. Blocker 03 is complete (summary +
  materiality ship). Extending the Interpreter's structured output with
  favored-party, category, and an attorney-review risk flag. Design decisions:
  favored-party is stored as a value *already relative to* the negotiation's
  `represented_party` (`represented` / `counterparty` / `neutral`) — the
  interpreter is handed `represented_party` so its decision is relative, and the
  UI maps `represented`→"Favors me", `counterparty`→"Favors them". Category and
  favored-party become domain enums (like `Materiality`); `risk_flag` stays a
  free-text review-prompt string (None when no risk). No migration —
  `category`/`favored_party`/`risk_flag` columns already exist (nullable) from
  `0001`. Filters extend `ChangeFilters` (+`risk` boolean) and the feed route.
  Tests written first.

- 2026-07-11 (agent): Completed. All acceptance criteria met; tests written
  first and passing (58 backend, 11 frontend; `tsc -b` + `vite build` clean).
  - **Domain**: added `Category` (payment/liability/ip/termination/
    confidentiality/other) and `FavoredParty` (represented/counterparty/neutral)
    enums; `Change.category`/`Change.favored_party` are now those enums (like
    `Materiality`), `risk_flag` stays free text. Favored-party is stored
    *relative to* `represented_party` so the UI needs no party names to render
    "favors me/them".
  - **Interpreter**: `InterpretationRequest` gained `represented_party`;
    `Interpretation` gained `category`/`favored_party`/`risk_flag` (all optional,
    so issue-03 call sites and the cosmetic path are unaffected). `FakeInterpreter`
    takes canned values for the three and records received requests
    (`.requests`) so the represented-party threading is assertable.
    `AzureOpenAIInterpreter` prompt/parse extended to emit all five fields, with
    risk framed strictly as a review prompt.
  - **Pipeline/service**: `interpret_changes(changes, interpreter,
    represented_party)` fills the new fields on material changes only (cosmetic
    changes stay `None`); `RoundService` fetches the negotiation's
    `represented_party` and threads it in. Decision #1 invariant intact — the
    stage still only annotates.
  - **Feed/API**: `ChangeFilters` gained `risk: bool`; `_matches` compares enum
    `.value`s and treats `risk` as has-a-flag. `/rounds/{id}/changes` gained a
    `risk` query param (category/favored_party already existed). DTO/repos
    serialize the enums via `.value` and rehydrate via the enum ctor.
  - **Frontend**: `ChangeCard` renders a favored-party badge, category tag, and a
    risk-flag review prompt (each omitted when null). `ChangeFeed` adds category
    + favored-party `<select>`s and a "flagged for review only" checkbox, all
    re-querying server-side via a new `ChangeFeedFilters` arg to
    `getRoundChanges`.
  - **No migration** — `category`/`favored_party`/`risk_flag` columns already
    exist (nullable) from `0001`.
  - **Deviations**: favored-party is a relative enum rather than a stored party
    name (rationale in the claim note); category is a closed vocab with `other`
    as the catch-all for the glossary's "etc.".
