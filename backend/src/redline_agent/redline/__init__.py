"""Standalone tracked-changes export.

``redline(prev_docx, curr_docx)`` paragraph-aligns two ``.docx`` documents,
word-diffs the modified paragraphs, and injects ``w:ins``/``w:del`` markup into
a copy of the prior document's OOXML — a Word deliverable that redlines the
latest round against the prior one.

This package is intentionally independent of the pipeline and domain layers
(decision #4): it imports nothing from them, so a pipeline bug can never corrupt
the deliverable and the export is testable in isolation via golden files.
"""

from __future__ import annotations

from redline_agent.redline.ooxml_writer import build_redline

# A fixed default so golden-file tests are deterministic; callers (the export
# service) pass the submitting round's timestamp in production.
_DEFAULT_DATE = "1970-01-01T00:00:00Z"

__all__ = ["redline"]


def redline(
    prev_docx: bytes,
    curr_docx: bytes,
    author: str = "Redline Agent",
    date: str = _DEFAULT_DATE,
) -> bytes:
    """Redline the current document against the prior; return ``.docx`` bytes.

    Latest-vs-prior only. Changes are attributed to ``author`` (the submitting
    party). A moved paragraph renders as delete + insert (accepted tradeoff).
    """
    return build_redline(prev_docx, curr_docx, author=author, date=date)
