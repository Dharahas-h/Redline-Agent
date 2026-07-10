# Redline Agent

Multi-round negotiation tracker for `.docx` legal contracts. Contributors — human
or agent — orient from the docs below, then pick up work from the backlog.

## Read first (in this order)
- `.scratch/README.md` — the feature backlog in priority order; each feature's
  PRD sits beside its `issues/`
- `ARCHITECTURE.md` — folder structure, layering rules, test seams
- `GLOSSARY.md` — domain vocabulary; use these exact terms in code, APIs, and UI
- `docs/decisions.md` — locked constraints and their rationale (do not violate
  without a human decision)

## Picking up work
Features live under `.scratch/<feature-slug>/`, each with a `PRD.md` and an
`issues/` directory of dependency-numbered issues. `.scratch/README.md` lists
features in priority order.

Status strings use the canonical triage labels in
`.claude/docs/triage-labels.md` (`ready-for-agent`, `ready-for-human`,
`wontfix`). Do not invent new status strings.

1. Read `.scratch/README.md`. Consider features top-down; skip any marked
   `wontfix`.
2. Within the highest-priority remaining feature, pick an issue whose
   `Status: ready-for-agent` AND whose every "Blocked by" issue is complete
   (all acceptance-criteria checkboxes ticked). Prefer the lowest-numbered
   eligible issue.
3. If that feature has no eligible issue (all complete, blocked, or already
   claimed), move to the next feature in the index.
4. Never start a blocked issue, a `ready-for-human` / HITL issue, or an issue in
   a `wontfix` feature.
5. Before starting, add a `## Comments` note claiming the issue so parallel
   agents do not collide. An issue is complete when every acceptance-criteria
   checkbox is ticked; when a feature's issues are all complete, remove it from
   the backlog table in `.scratch/README.md`.
6. Append what you did (decisions, deviations, follow-ups) to the `## Comments`
   section at the bottom of the issue file.

## How to work an issue
- Implement exactly the vertical slice described — end to end, through every
  tier. Don't pull scope forward from later issues; don't leave a tier stubbed.
- Follow the existing patterns, layering, and naming. Match the surrounding
  code's style rather than introducing new conventions. Respect the constraints
  in `docs/decisions.md` and the layering in `ARCHITECTURE.md`.
- Write the test first, then the code (TDD). Prefer the highest existing test
  seam; test external behavior, not implementation details. External
  dependencies go through Protocols with fakes — no test hits the network.
- If the issue is ambiguous or its assumptions turn out wrong, stop and record
  the blocker in the issue's Comments rather than guessing.

## Definition of done
Acceptance criteria met · tests written-first and passing · glossary terms used
· issue Status updated · Comments appended · no unrelated changes.
