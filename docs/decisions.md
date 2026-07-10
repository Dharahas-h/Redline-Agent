# Decisions

Locked constraints and their rationale. Do not violate these without a human
decision — the rationale is the part most likely to be forgotten.

## 1. Deterministic diff is the source of truth; the LLM never invents changes
The deterministic differ decides WHAT changed. The LLM only explains what a
change MEANS (summary, materiality, category, favored-party, risk). It never
detects, adds, or removes changes.
**Why:** legal output must be auditable and reproducible; a hallucinated or
silently missed change can bind a client to terms they never intended.
**Enforced by:** an invariant test — a garbage-returning `FakeInterpreter` must
not alter the set of detected changes.

## 2. Deterministic pipeline, not an autonomous agent loop
Orchestration code calls the LLM at fixed, bounded steps. The model never
decides what to do next.
**Why:** predictability, testability, and auditability for legal-facing output.
A conversational/agentic layer over history is deferred to a later version.

## 3. `.docx` is the anchor format; rounds arrive clean
Rounds are treated as clean documents and we compute our own diff. We do not
rely on incoming tracked changes being present.
**Why:** a counterparty leaving track-changes on is not something we can depend
on; computing the diff ourselves is correct regardless of incoming markup.

## 4. The export is a standalone package, independent of the pipeline
`redline(prev_docx, curr_docx) -> docx` imports nothing from pipeline/domain.
It paragraph-aligns the two documents, word-diffs modified paragraphs, and
injects `w:ins`/`w:del` into a copy of the prior document's original OOXML.
Latest-vs-prior only.
**Why:** a pipeline bug can never corrupt the deliverable, and it is testable in
isolation via golden files. Accepted tradeoff: a moved paragraph renders as
delete + insert.

## 5. Human-in-the-loop trust model
Alignment carries a confidence; low-confidence matches are flagged. Users can
override alignment, which regenerates the diff and interpretation. Every
interpreted change links to its raw before/after. All output is framed as
attorney work-product for review.
**Why:** the human stays the decision-maker; the tool never presents machine
output as final or as legal advice.

## 6. Content-handling triage for v1
Defined-term definition changes are detected and flagged with a reference
ripple count. Tables are detect-and-flag only (no cell-level diff). Exhibits are
treated as ordinary sections. Cross-reference tracking is out of scope.
**Why:** defined-terms are cheap and high-value; a cell-level table diff would
emit misleading garbage, so a manual-review flag is safer.

## 7. Pluggable LLM behind a Protocol; provider terms are gating
`LLMInterpreter` and `Embedder` are Protocols. Default embeddings: Azure
`text-embedding-3-large`. Default interpreter: Azure OpenAI, with Claude
benchmarked as an alternative before locking in.
**Why:** interpretation quality only shows on real contracts, so the model must
be swappable and benchmarked. Enterprise no-training / data-residency terms are
a hard requirement for any provider handling legal documents.

## 8. Tenant-ready schema, but no auth in v1
`tenant_id` is present from the first migration, but v1 operates single-tenant
with no authentication.
**Why:** retrofitting tenant isolation is painful, so bake it in now; auth is
deferred. Consequence: the service must NOT be exposed on a network with real
client data until authentication exists.
