"""Segmenter stage.

Splits a round's canonical text into clauses using the document's heading and
numbering structure. A clause is a logical unit (a numbered section, a heading
block, etc.) and is the unit of alignment, diffing, and display.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A numbered start: multi-level ("1.1", "2.3.4") optionally punctuated, or a
# single integer that MUST carry a "." or ")" separator so that prose like
# "30 days notice" is not mistaken for a clause number.
_MULTILEVEL = re.compile(r"^(\d+(?:\.\d+)+)[.)]?\s+(.+)$")
_SINGLE = re.compile(r"^(\d+)[.)]\s+(.+)$")
# An all-caps heading line (allowing digits and common punctuation).
_ALLCAPS = re.compile(r"^[A-Z0-9][A-Z0-9 ,&()'\-/.]*$")

_HEADING_MAX_LEN = 60


@dataclass
class SegmentedClause:
    """A clause produced by segmentation, before it is bound to a round."""

    ordinal: int
    text: str
    number_label: str | None = None
    heading: str | None = None


def _match_start(line: str) -> tuple[str | None, str | None] | None:
    """Return ``(number_label, heading)`` if ``line`` starts a clause, else None."""
    for pattern in (_MULTILEVEL, _SINGLE):
        m = pattern.match(line)
        if m:
            number_label = m.group(1).rstrip(".)")
            rest = m.group(2).strip()
            heading = rest if len(rest) <= _HEADING_MAX_LEN and not rest.endswith(".") else None
            return number_label, heading
    if _ALLCAPS.match(line) and sum(c.isalpha() for c in line) >= 2 and len(line) <= _HEADING_MAX_LEN:
        return None, line
    return None


def segment(canonical_text: str) -> list[SegmentedClause]:
    """Segment canonical text into ordered clauses."""
    lines = [line for line in canonical_text.split("\n") if line.strip()]
    if not lines:
        return []

    blocks: list[dict] = []
    current: dict | None = None
    for line in lines:
        start = _match_start(line)
        if start is not None:
            number_label, heading = start
            current = {"number_label": number_label, "heading": heading, "lines": [line]}
            blocks.append(current)
        elif current is None:
            # Preamble text before the first recognized heading/number.
            current = {"number_label": None, "heading": None, "lines": [line]}
            blocks.append(current)
        else:
            current["lines"].append(line)

    return [
        SegmentedClause(
            ordinal=i,
            text="\n".join(b["lines"]),
            number_label=b["number_label"],
            heading=b["heading"],
        )
        for i, b in enumerate(blocks)
    ]
