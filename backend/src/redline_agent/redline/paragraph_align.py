"""Paragraph alignment for the tracked-changes export.

Aligns the prior and current documents' body paragraphs by an LCS over their
normalized text (``difflib.SequenceMatcher``). Each output op is one of:

- ``equal``    — paragraph unchanged (kept verbatim from prior)
- ``modified`` — paragraph edited in place (word-level diff applied)
- ``delete``   — paragraph present only in the prior document
- ``insert``   — paragraph present only in the current document

Within a ``replace`` region, prior/current paragraphs are paired positionally
and kept as ``modified`` only when they are similar enough; dissimilar pairs
degrade to delete + insert. A moved paragraph therefore renders as delete +
insert (the accepted tradeoff in decision #4), never as a spurious modify.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

Kind = str  # "equal" | "modified" | "delete" | "insert"

_WHITESPACE = re.compile(r"\s+")

# Minimum similarity for two paragraphs in a replace region to be treated as a
# single modified paragraph rather than an unrelated delete + insert.
_MODIFIED_THRESHOLD = 0.5


@dataclass(frozen=True)
class ParaOp:
    """One alignment decision, referencing prior/current paragraph indices."""

    kind: Kind
    prev_index: int | None = None
    curr_index: int | None = None


def normalize(text: str) -> str:
    """Collapse whitespace and strip, for text-equality alignment."""
    return _WHITESPACE.sub(" ", text).strip()


def align_paragraphs(
    prev_texts: list[str],
    curr_texts: list[str],
    modified_threshold: float = _MODIFIED_THRESHOLD,
) -> list[ParaOp]:
    """Align prior/current paragraph texts into an ordered list of ops."""
    prev = [normalize(t) for t in prev_texts]
    curr = [normalize(t) for t in curr_texts]
    matcher = SequenceMatcher(a=prev, b=curr, autojunk=False)

    ops: list[ParaOp] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                ops.append(ParaOp("equal", i1 + offset, j1 + offset))
        elif tag == "delete":
            ops.extend(ParaOp("delete", prev_index=i) for i in range(i1, i2))
        elif tag == "insert":
            ops.extend(ParaOp("insert", curr_index=j) for j in range(j1, j2))
        elif tag == "replace":
            ops.extend(
                _pair_replace(prev, curr, i1, i2, j1, j2, modified_threshold)
            )
    return ops


def _pair_replace(
    prev: list[str],
    curr: list[str],
    i1: int,
    i2: int,
    j1: int,
    j2: int,
    threshold: float,
) -> list[ParaOp]:
    ops: list[ParaOp] = []
    paired = min(i2 - i1, j2 - j1)
    for offset in range(paired):
        i, j = i1 + offset, j1 + offset
        ratio = SequenceMatcher(a=prev[i], b=curr[j]).ratio()
        if ratio >= threshold:
            ops.append(ParaOp("modified", i, j))
        else:
            ops.append(ParaOp("delete", prev_index=i))
            ops.append(ParaOp("insert", curr_index=j))
    ops.extend(ParaOp("delete", prev_index=i) for i in range(i1 + paired, i2))
    ops.extend(ParaOp("insert", curr_index=j) for j in range(j1 + paired, j2))
    return ops
