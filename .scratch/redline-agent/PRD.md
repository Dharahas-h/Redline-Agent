# PRD: Redline Agent

Status: ready-for-agent

## Problem Statement

Legal teams negotiate contracts over many rounds. Each round a party sends back a revised `.docx` — usually a "clean" document, not one with tracked changes left on. To understand what moved, a lawyer today must manually run Word's Compare (or eyeball it), then read every changed clause to work out what each edit *means*, whether it is substantive or cosmetic, and whether it helps or hurts their side. Across a long negotiation there is no reliable way to see how a single clause evolved over time, or to get a fast "what changed against us this round" read. Mistakes are costly: a silently missed material change can bind a client to terms they never intended.

## Solution

A stateful, multi-round negotiation tracker for `.docx` legal documents. A user creates a negotiation, declares which party they represent, and uploads each new round as it arrives. For every round the system deterministically computes what changed versus the prior round, interprets each change in plain English (what it means, whether it is material, its category, whom it favors, and whether it warrants attorney review), and tracks how every clause evolves across the whole negotiation.

The primary experience is an interactive, clause-centric change feed: the changes this round, filterable by materiality/category/favored-party, each with before/after text and interpretation, with drill-through to a clause's full cross-round lineage. Uncertain clause matches are flagged and can be corrected by the user. The user can also download a tracked-changes `.docx` (latest round vs. prior) that opens cleanly in Word as a drop-in deliverable.

Core principle: a **deterministic diff decides what changed; the LLM only ever explains what it means.** The model never invents or detects changes.

## User Stories

1. As a lawyer, I want to create a negotiation for a contract, so that I have one place to track its evolution.
2. As a lawyer, I want to declare which party I represent when creating a negotiation, so that the system can tell me whether each change favors me or the other side.
3. As a lawyer, I want to upload a new round as a `.docx`, so that the system ingests and tracks it.
4. As a lawyer, I want each uploaded round stored faithfully (the original file preserved), so that I can always retrieve exactly what was exchanged.
5. As a lawyer, I want to see the list of rounds in a negotiation with who submitted each and when, so that I understand the negotiation timeline.
6. As a lawyer, I want the system to compute what changed between the newest round and the prior one, so that I do not have to run Word Compare manually.
7. As a lawyer, I want changes presented per clause rather than as raw character noise, so that I can reason about them the way I think about the contract.
8. As a lawyer, I want to see the exact before/after text for each changed clause, so that I can verify the change myself against a trustworthy source.
9. As a lawyer, I want a plain-English summary of each change, so that I can grasp it quickly.
10. As a lawyer, I want each change classified as substantive or cosmetic, so that I can filter out typos and formatting noise.
11. As a lawyer, I want each change tagged by category (payment, liability, IP, termination, confidentiality, etc.), so that I can focus on the areas I care about.
12. As a lawyer, I want each change labeled as favoring me or the counterparty, so that I can see at a glance what this round cost or gained me.
13. As a lawyer, I want unusual or aggressive terms flagged for attorney review, so that I do not overlook risky edits — framed as prompts for review, not legal conclusions.
14. As a lawyer, I want to filter the change feed by materiality, category, and favored-party, so that I can zero in on what matters.
15. As a lawyer, I want to click a clause and see how it changed across every round, so that I can understand the trajectory of a negotiation point.
16. As a lawyer, I want uncertain clause matches flagged, so that I know where the system's automatic pairing might be wrong.
17. As a lawyer, I want to manually correct a clause pairing (re-pair, split, or merge), so that the diff reflects reality when the automatic match is wrong.
18. As a lawyer, I want the diff and interpretation to regenerate after I correct an alignment, so that my correction propagates.
19. As a lawyer, I want to be warned when a defined term's definition changes, along with how many clauses reference it, so that I appreciate the ripple effect of a definitional edit.
20. As a lawyer, I want to be told when a table (e.g. a pricing schedule) has changed and prompted to review it manually, so that I am not misled by a garbled cell-level diff.
21. As a lawyer, I want to download a tracked-changes `.docx` of the latest round versus the prior one, so that I have a Word deliverable to review or forward.
22. As a lawyer, I want the downloaded redline to preserve the original document's formatting and numbering, so that it is a professional, drop-in artifact.
23. As a lawyer, I want the redline's changes attributed to the submitting party, so that it reads like a normal marked-up document.
24. As a lawyer, I want interpretations always framed as machine-generated work-product for attorney review, so that I retain professional judgment and the tool never overstates certainty.
25. As a lawyer, I want the underlying raw before/after always visible behind any summary, so that the LLM's prose is never the only evidence I rely on.
26. As a developer, I want the tracked-changes export to be an independent function of two `.docx` files, so that a pipeline bug can never corrupt the deliverable and it can be tested in isolation.
27. As a developer, I want the interpretation model to be swappable, so that we can benchmark and switch providers without rewriting the pipeline.
28. As an administrator, I want the schema tenant-ready from day one, so that multi-tenant operation can be added later without a painful migration.

## Implementation Decisions

**Architecture.** Deterministic pipeline (no autonomous agent loop). Layering is inward-only: `api → services → pipeline/domain → repositories → infra`. The tracked-changes export lives in a standalone `redline` package that imports nothing from the pipeline/domain.

**Pipeline stages (per uploaded round):** Ingestor (flatten `.docx` to canonical normalized text, store original blob by reference, persist snapshot) → Segmenter (structure-based clause segmentation from heading/numbering) → Aligner (embedding-similarity + clause-number/heading match; LLM adjudicates only ambiguous splits/merges/moves) → Differ (word-level diff of aligned clauses = ground truth) → Interpreter (per-change, concurrent, cached, material-only LLM call returning structured JSON). Cost scales with change size, not document size; unchanged/cosmetic clauses skip interpretation.

**Format.** `.docx` is the anchor format. Rounds arrive "clean" (no reliance on incoming tracked changes); the system computes its own diff. PDF/tracked-changes-parsing are out of scope.

**Interpretation output (structured schema):** summary, materiality (substantive/cosmetic), category, favored-party, attorney-review risk flag. Favored-party is computed relative to the negotiation's `represented_party`. Risk is framed as review prompts, not conclusions.

**Export.** Standalone `redline(prev_docx, curr_docx) -> docx`, latest-vs-prior only. Algorithm: paragraph-align (`w:p` LCS on normalized text) → classify each paragraph unchanged/inserted/deleted/modified → word-level diff within modified paragraphs → inject `w:ins`/`w:del` markup into a copy of the prior document's original OOXML (formatting-preserving), attributed to the submitting party. Fully independent of the pipeline; accepted tradeoff is that moved paragraphs render as delete+insert noise.

**Content handling.** Defined-term definition changes are detected and flagged with reference-count ripple. Tables are detect-and-flag only (no cell-level diff). Exhibits/schedules are treated as ordinary sections. Cross-reference tracking is out of scope.

**Trust / human-in-the-loop.** Alignment carries a confidence (from embedding similarity + whether LLM fallback fired); low-confidence pairings are flagged. Users can override alignment (re-pair/split/merge), which regenerates the diff and interpretation. Every interpreted change links to its deterministic raw before/after. All output framed as attorney work-product.

**Storage / schema (Postgres + Azure Blob, tenant-ready from migration #1):**
- `negotiations` (id, tenant_id, title, represented_party, created_at)
- `rounds` (id, negotiation_id, round_no, submitted_by_party, blob_uri, canonical_text, status, created_at) — full snapshot per round; diffs are derived/regenerable
- `clauses` (id, round_id, ordinal, number_label, heading, text, embedding)
- `clause_lineage` (id, negotiation_id, prev_clause_id, curr_clause_id, similarity, confidence, align_method, overridden)
- `changes` (id, negotiation_id, from_round_id, to_round_id, curr_clause_id, change_type, raw_before, raw_after, summary, materiality, category, favored_party, risk_flag, interpretation_model) — interpretation columns nullable until interpreted

**API contracts (REST/JSON):**
- `POST /negotiations`, `GET /negotiations`, `GET /negotiations/{id}`
- `POST /negotiations/{id}/rounds` (multipart upload; runs pipeline as a background task), `GET /negotiations/{id}/rounds`
- `GET /rounds/{id}/changes` (clause-centric feed; filters: materiality, category, favored_party), with round `status` for polling
- `GET /changes/{id}` (single change + raw before/after)
- `GET /clauses/{id}/lineage` (cross-round evolution)
- `PATCH /rounds/{id}/alignment` (human override → regenerates diff/interpretation)
- `POST /negotiations/{id}/export` (latest-vs-prior tracked-changes .docx), `GET /exports/{id}` (download)

**External dependencies behind Protocols (swappable):** `Embedder` (Azure `text-embedding-3-large`), `LLMInterpreter` (pluggable; default Azure OpenAI, Claude benchmarked as alternative), `BlobStore` (Azure Blob). Enterprise no-training / data-residency terms are a gating requirement for whichever LLM provider is used.

**Async.** Uploads run the pipeline as a background task with round `status` polling (in-process for v1; a task queue is a later swap).

**Stack.** Python + FastAPI backend (tracked-changes writing isolated in the `redline` package's lxml-based OOXML writer); React + TypeScript SPA. Signature view: clause-centric interpreted change feed with drill-through to lineage. No authentication in v1 — the service must not be network-exposed with real client data until auth exists.

## Testing Decisions

**Approach: test-driven — tests are written first for every slice.** A good test asserts external behavior at a seam, never implementation details, and runs deterministically and offline.

**Seams (highest available):**
- **Protocol seams** — `Embedder`, `LLMInterpreter`, `BlobStore` are injected as fakes (`FakeEmbedder` returns deterministic vectors keyed on text; `FakeInterpreter` returns canned structured output; `InMemoryBlobStore`). No pipeline or service test touches the network.
- **`RoundService` orchestration seam** — the highest-value integration test: feed a `.docx` fixture with all fakes injected and a real Postgres (transaction rolled back per test), assert the persisted Clauses/Changes and the returned feed.
- **API seam** — `httpx.AsyncClient` behavioral tests per route (status, response shape, filters, alignment-override regeneration, background-task status transitions).
- **`redline()` public-function seam** — golden-file tests: hand-crafted `prev.docx`/`curr.docx` pairs (insertion, deletion, modified paragraph, moved paragraph documenting accepted move-noise) → assert the emitted OOXML contains the correct `w:ins`/`w:del` and opens cleanly in Word.
- **Frontend API boundary** — Vitest + React Testing Library with MSW-mocked responses for `ChangeFeed`/`ChangeCard`/`AlignmentOverride`.

**Core invariant as an executable test:** with a `FakeInterpreter` returning garbage, the set of `Change` rows must equal exactly what the deterministic Differ produced — encoding "the LLM never invents changes" as a test, not a hope.

**Modules under test:** every pipeline stage (flatten, segmenter, aligner incl. low-confidence/LLM-fallback cases, differ, interpreter, defined_terms), the `redline` package, repositories (against real Postgres, asserting tenant-scoping and lineage queries), services, API routers, and the signature React components.

**Tooling:** `pytest` + `pytest-asyncio`, `httpx.AsyncClient`, golden `.docx` fixtures, `factory-boy` for DB fixtures; Vitest + RTL + MSW on the frontend. CI coverage gate as a floor, not a target.

## Out of Scope

- Autonomous agentic Q&A over negotiation history (deferred to a later version).
- Arbitrary-round-pair export (v1 is latest-vs-prior only).
- Table cell-level diffing (detect-and-flag only in v1).
- Cross-reference tracking on renumbering.
- PDF import and parsing of incoming tracked-changes/comments.
- Multi-tenant operation (schema is tenant-ready, but operation is single-tenant).
- Authentication and authorization.
- Google Docs / non-`.docx` formats.

## Further Notes

- The clause segmentation/alignment layer is the backbone the whole pipeline leans on; alignment quality gates interpretation quality and the lineage view.
- The biggest historical risk (mapping flattened-text changes back onto OOXML) is sidestepped by making the export a standalone paragraph-anchored function operating directly on the two original documents.
- A human evaluation of interpretation quality (Azure OpenAI vs. Claude, prompt tuning) on real contracts is required before locking the default interpretation model — this is a human-in-the-loop step, not an automated one.
