"""Word-level diff within a modified paragraph.

Splits two paragraph texts into whitespace-delimited words and returns an
ordered list of segments (kept / inserted / deleted), which the OOXML writer
turns into plain runs, ``w:ins`` runs, and ``w:del`` runs. Whitespace is
normalized to single spaces; exact intra-paragraph spacing is not preserved
(an accepted v1 simplification — the redline stays legible).
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

Op = str  # "equal" | "insert" | "delete"


@dataclass(frozen=True)
class WordSeg:
    """A run of words sharing one edit operation."""

    op: Op
    text: str


def diff_words(before: str, after: str) -> list[WordSeg]:
    """Return ordered word-level segments turning ``before`` into ``after``."""
    a = before.split()
    b = after.split()
    matcher = SequenceMatcher(a=a, b=b, autojunk=False)
    segments: list[WordSeg] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            segments.append(WordSeg("equal", " ".join(a[i1:i2])))
        elif tag == "delete":
            segments.append(WordSeg("delete", " ".join(a[i1:i2])))
        elif tag == "insert":
            segments.append(WordSeg("insert", " ".join(b[j1:j2])))
        elif tag == "replace":
            segments.append(WordSeg("delete", " ".join(a[i1:i2])))
            segments.append(WordSeg("insert", " ".join(b[j1:j2])))
    return [s for s in segments if s.text]
