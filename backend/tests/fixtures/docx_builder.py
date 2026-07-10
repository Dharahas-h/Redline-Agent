"""Helpers to build in-memory .docx fixtures for tests.

Tests construct documents from a list of paragraph strings (optionally tagged
with a Word style name) so no binary fixture files need to be committed for the
common cases.
"""

from __future__ import annotations

import io

from docx import Document


def make_docx(paragraphs: list[str | tuple[str, str]]) -> bytes:
    """Build a .docx from paragraph specs and return its bytes.

    Each item is either a plain string (Normal style) or a ``(style, text)``
    tuple, where ``style`` is a Word style name such as ``"Heading 1"``.
    """
    document = Document()
    for para in paragraphs:
        if isinstance(para, tuple):
            style, text = para
            document.add_paragraph(text, style=style)
        else:
            document.add_paragraph(para)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
