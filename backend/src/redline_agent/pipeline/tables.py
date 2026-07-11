"""Tables stage.

Tables are detect-and-flag only: a changed table raises a manual-review alert,
never a cell-level diff (decision #6) — a cell diff would emit misleading
garbage. A table's *signature* is the flattened text of all its cells; comparing
signatures positionally between rounds tells us which tables changed without
interpreting how.

Because ``flatten_docx`` drops tables from canonical text, signatures are
extracted straight from the ``.docx`` bytes and carried on the round.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from docx import Document

_WHITESPACE = re.compile(r"\s+")


def extract_table_signatures(data: bytes) -> list[str]:
    """One flattened, whitespace-normalized signature per top-level table."""
    document = Document(io.BytesIO(data))
    signatures: list[str] = []
    for table in document.tables:
        cells = [
            _WHITESPACE.sub(" ", cell.text).strip()
            for row in table.rows
            for cell in row.cells
        ]
        signatures.append(" | ".join(cells))
    return signatures


@dataclass
class TableChange:
    """A changed table, identified by 1-based position and how it changed."""

    position: int
    kind: str  # "added" | "removed" | "modified"


def detect_table_changes(
    prev_signatures: list[str], curr_signatures: list[str]
) -> list[TableChange]:
    """Compare table signatures positionally; report each table that differs.

    Positional (not content) matching mirrors the export's paragraph alignment
    (decision #4): a reordered table reads as removed + added, which is a safe,
    review-prompting outcome for a detect-and-flag surface.
    """
    changes: list[TableChange] = []
    for i in range(max(len(prev_signatures), len(curr_signatures))):
        prev = prev_signatures[i] if i < len(prev_signatures) else None
        curr = curr_signatures[i] if i < len(curr_signatures) else None
        if prev == curr:
            continue
        if prev is None:
            kind = "added"
        elif curr is None:
            kind = "removed"
        else:
            kind = "modified"
        changes.append(TableChange(position=i + 1, kind=kind))
    return changes
