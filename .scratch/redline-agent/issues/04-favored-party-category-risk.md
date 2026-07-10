# See what each change costs me

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Turn the feed into a negotiation tool: each change shows whether it favors the party the user represents or the counterparty, a category tag (payment, liability, IP, termination, confidentiality, etc.), and an attorney-review risk flag. The user can filter by favored-party, category, and risk.

Extends the Interpreter's structured output to include favored-party (computed relative to the negotiation's `represented_party` captured in Slice 1), category, and a risk flag framed as a prompt for attorney review — never a legal conclusion.

## Acceptance criteria

- [ ] Each change shows a favored-party badge (favors me / favors them) derived from `represented_party`
- [ ] Each change shows a category tag and an attorney-review risk flag
- [ ] The feed can be filtered by favored-party, category, and risk
- [ ] Risk output is phrased as a review prompt, and all output is framed as attorney work-product
- [ ] Tests written first: interpreter output schema with `FakeInterpreter`; favored-party correctness relative to `represented_party`; feed filter behavior; React badge/filter components

## Blocked by

- `.scratch/redline-agent/issues/03-plain-english-change-summaries.md`
