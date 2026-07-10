# Download a redline of the latest round

Status: ready-for-agent
Type: AFK

## Parent

`.scratch/redline-agent/PRD.md`

## What to build

A standalone tracked-changes `.docx` export. The user clicks Export on a negotiation and downloads a Word document that redlines the latest round against the prior one and opens cleanly in Word.

The export is a self-contained `redline(prev_docx, curr_docx) -> docx` function that imports nothing from the pipeline. Algorithm: paragraph-align the two documents (`w:p` LCS on normalized text) → classify each paragraph unchanged / inserted / deleted / modified → run a word-level diff within modified paragraphs → inject `w:ins`/`w:del` markup into a copy of the prior document's original OOXML so all formatting and numbering are preserved, attributed to the submitting party. Latest-vs-prior only. Accepted tradeoff: a moved paragraph renders as delete + insert.

## Acceptance criteria

- [ ] `redline(prev, curr)` produces valid tracked-changes OOXML that opens cleanly in Word
- [ ] Insertions, deletions, and intra-paragraph modifications are marked with correct `w:ins`/`w:del`
- [ ] Original formatting/numbering from the prior document is preserved (markup injected into a copy of its OOXML)
- [ ] Changes are attributed to the submitting party
- [ ] `POST /negotiations/{id}/export` generates the latest-vs-prior redline; `GET /exports/{id}` downloads it
- [ ] React app has a working Export/download control
- [ ] The `redline` package has no import dependency on the pipeline/domain packages
- [ ] Tests written first: golden-file `.docx` cases covering insertion, deletion, modified paragraph, and a moved paragraph (documenting the accepted move-noise)

## Blocked by

- `.scratch/redline-agent/issues/01-skeleton-upload-rounds-see-changes.md` (needs two stored rounds)
