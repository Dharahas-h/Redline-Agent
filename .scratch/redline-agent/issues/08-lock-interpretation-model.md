# Lock the interpretation model

Status: ready-for-human
Type: HITL

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

Human evaluation to choose and lock the default interpretation model and prompt. Run the same interpretation prompt through the candidate providers (Azure OpenAI and Claude) on a set of real contracts via the swappable `LLMInterpreter` Protocol, review the quality of summaries, materiality, category, favored-party, and risk flags, tune the prompt, and set the default. Confirm enterprise no-training / data-residency terms for the chosen provider.

This requires human legal judgment on interpretation quality and cannot be validated by automated tests alone.

## Acceptance criteria

- [ ] Same prompt run through Azure OpenAI and Claude on a real-contract evaluation set
- [ ] Human review comparing interpretation quality across providers
- [ ] Default model and prompt selected and configured
- [ ] Enterprise no-training / data-residency terms confirmed for the chosen provider

## Blocked by

- `.scratch/redline-agent/issues/04-favored-party-category-risk.md`
