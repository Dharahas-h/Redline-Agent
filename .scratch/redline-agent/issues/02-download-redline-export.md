# Download a redline of the latest round

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

A standalone tracked-changes `.docx` export. The user clicks Export on a negotiation and downloads a Word document that redlines the latest round against the prior one and opens cleanly in Word.

The export is a self-contained `redline(prev_docx, curr_docx) -> docx` function that imports nothing from the pipeline. Algorithm: paragraph-align the two documents (`w:p` LCS on normalized text) → classify each paragraph unchanged / inserted / deleted / modified → run a word-level diff within modified paragraphs → inject `w:ins`/`w:del` markup into a copy of the prior document's original OOXML so all formatting and numbering are preserved, attributed to the submitting party. Latest-vs-prior only. Accepted tradeoff: a moved paragraph renders as delete + insert.

## Acceptance criteria

- [x] `redline(prev, curr)` produces valid tracked-changes OOXML that opens cleanly in Word
- [x] Insertions, deletions, and intra-paragraph modifications are marked with correct `w:ins`/`w:del`
- [x] Original formatting/numbering from the prior document is preserved (markup injected into a copy of its OOXML)
- [x] Changes are attributed to the submitting party
- [x] `POST /negotiations/{id}/export` generates the latest-vs-prior redline; `GET /exports/{id}` downloads it
- [x] React app has a working Export/download control
- [x] The `redline` package has no import dependency on the pipeline/domain packages
- [x] Tests written first: golden-file `.docx` cases covering insertion, deletion, modified paragraph, and a moved paragraph (documenting the accepted move-noise)

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md` (needs two stored rounds)

## Comments

- 2026-07-11 (agent): Claiming this issue. Issue 01 (walking skeleton) is
  complete — two rounds are stored as original blobs. Building the standalone
  `redline` package (`paragraph_align`, `word_diff`, `ooxml_writer`) exposing
  `redline(prev_docx, curr_docx) -> bytes` with no pipeline/domain imports, an
  `exports` table + `ExportService`, `POST /negotiations/{id}/export` +
  `GET /exports/{id}`, and a frontend Export control. Tests written first
  (golden-file .docx cases: insertion, deletion, modified, moved).

- 2026-07-11 (agent): Completed. All acceptance criteria met; tests written
  first and passing (40 backend, 6 frontend; `tsc --noEmit` + `vite build`
  clean).
  - **Standalone `redline` package** (`backend/src/redline_agent/redline/`):
    `paragraph_align` (LCS over normalized paragraph text via
    `difflib.SequenceMatcher`; a replace region pairs paragraphs positionally
    and keeps a pair as `modified` only above a 0.5 similarity threshold, so a
    move degrades to delete + insert), `word_diff` (word-level segments within
    a modified paragraph), `ooxml_writer` (injects `w:ins`/`w:del` into a copy
    of the *prior* document's `word/document.xml`; every other zip entry —
    styles, numbering — is passed through untouched, so prior formatting is
    preserved verbatim). `__init__` exposes
    `redline(prev_docx, curr_docx, author=..., date=...) -> bytes`. Imports
    nothing from pipeline/domain (enforced by a test).
  - **Persistence + API**: `exports` table (ORM `ExportRow` + Alembic
    migration `0002_exports`, tenant-ready), `ExportRepository`,
    `ExportService` (fetches the two most recent rounds' original blobs, calls
    `redline()` with the latest round's party as author and its timestamp as
    the revision date, stores the result in the blob store), and routers
    `POST /negotiations/{id}/export` (201 → `ExportOut`; 400 when < 2 rounds,
    404 for unknown negotiation) + `GET /exports/{id}` (streams the `.docx`
    with attachment headers; 404 when missing).
  - **Frontend**: `createExport` / `exportDownloadUrl` client fns, `Export`
    type, `ExportButton` component (generate → surface a download `<a>` for the
    produced redline; error state when generation fails), wired into
    `NegotiationDetail`.
  - **Deviations / notes:**
    - `redline()`'s `date` defaults to a fixed constant so golden-file tests
      are deterministic; the service passes the real round timestamp.
    - Word-level diff normalizes intra-paragraph whitespace to single spaces
      (legible redline; exact original spacing within a *modified* paragraph is
      not preserved). Kept (`equal`) paragraphs are copied element-for-element,
      so their formatting is fully preserved; only changed paragraphs' runs are
      rebuilt (paragraph-level `w:pPr`/numbering is retained).
    - Export bytes live in the same `BlobStore` seam as round blobs
      (`InMemoryBlobStore` in dev/test; Azure Blob is the later swap).
