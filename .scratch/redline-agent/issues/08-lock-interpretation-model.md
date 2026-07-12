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

## Comments

- 2026-07-12 (agent): Wired the real interpretation model into the running
  pipeline (the "connect infra to code" prerequisite for the eval). Findings and
  changes:
  - **It was connected but never firing.** The code path
    (`config → build_interpreter → app.state.interpreter → RoundService →
    interpret_changes`) was complete, but `Settings` (env_prefix `REDLINE_`,
    fields `azure_openai_*`) didn't match the `.env` (`OPENAI_*`/`EMBEDDING_*`),
    so `build_interpreter`/`build_adjudicator`/`build_embedder` silently fell
    back to the offline fakes. The real model was never used.
  - **Client mismatch.** The impls used the classic
    `AsyncAzureOpenAI(azure_endpoint, api_version, deployment)` scheme, but the
    configured endpoint is an Azure AI Foundry OpenAI-compatible `/openai/v1/`
    surface. Refactored interpreter/adjudicator/embedder to the standard
    `AsyncOpenAI(base_url, api_key, model)` client (works with both Foundry v1
    and api.openai.com).
  - **Config**: replaced `azure_openai_*` with `openai_api_key/_base_url/_model`
    and `embedding_api_key/_base_url/_model`, each accepting the bare `OPENAI_*`/
    `EMBEDDING_*` names via `AliasChoices` so the existing `.env` works unchanged.
    Added `openai>=1.40` to deps.
  - **Verified live**: a real `interpret()` call to `gpt-5.1` returned correct
    structured output (liability category, favored-party relative to the
    represented party, risk framed as a review prompt); a real `text-embedding-
    3-large` call returned 3072-dim vectors.
  - **Test isolation fix**: the rename made the ambient `.env` suddenly live in
    tests, so API tests began building real network clients (one flipped
    `alignment_method` to `llm`). Fixed by constructing test `Settings` with
    `_env_file=None`. Full suite hermetic again: 106 passed in ~5s.
  - **Not done (still HITL, deferred per scope)**: the `ClaudeInterpreter`
    adapter, the Azure-vs-Claude comparison on a real-contract eval set, and
    confirming enterprise no-training / data-residency terms. Default is
    currently `gpt-5.1`; locking it awaits that human evaluation.
