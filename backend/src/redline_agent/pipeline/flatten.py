"""Ingestor / flatten stage.

Reads a .docx and produces canonical text: the flattened, whitespace-normalized
plain-text form of a round, used as the basis for segmentation and diffing.

Tables are intentionally not cell-diffed here (decision #6); only body
paragraphs contribute to canonical text in v1.
"""

from __future__ import annotations

import io
import re

from docx import Document

_WHITESPACE = re.compile(r"\s+")


def flatten_docx(data: bytes) -> str:
    """Flatten .docx bytes to canonical normalized text.

    Each body paragraph becomes one line; internal whitespace is collapsed to
    single spaces, lines are stripped, and empty paragraphs are dropped.
    """
    document = Document(io.BytesIO(data))
    lines: list[str] = []
    for paragraph in document.paragraphs:
        normalized = _WHITESPACE.sub(" ", paragraph.text).strip()
        if normalized:
            lines.append(normalized)
    return "\n".join(lines)
