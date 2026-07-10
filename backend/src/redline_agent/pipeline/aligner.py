"""Aligner stage (positional).

Matches each current-round clause to its counterpart in the prior round. This
skeleton uses trivial positional alignment: pair by clause number label where
present, otherwise by ordinal position. Embedding-similarity alignment and the
LLM adjudicator arrive in a later slice.
"""

from __future__ import annotations

from dataclasses import dataclass

from redline_agent.domain import AlignMethod, Clause


@dataclass
class AlignmentPair:
    """A prior/current clause pairing. Either side may be None."""

    prev: Clause | None
    curr: Clause | None
    align_method: AlignMethod = AlignMethod.POSITIONAL
    similarity: float | None = None
    confidence: float = 1.0


def align_positional(prev: list[Clause], curr: list[Clause]) -> list[AlignmentPair]:
    """Align current clauses to prior clauses by number label then ordinal.

    Output preserves current-round order; clauses present only in the prior
    round (removed) are appended at the end.
    """
    prev_by_label: dict[str, Clause] = {
        c.number_label: c for c in prev if c.number_label
    }
    used: set[int] = set()

    # Pass 1: match by number label.
    label_match: dict[int, Clause] = {}
    for c in curr:
        if c.number_label and c.number_label in prev_by_label:
            p = prev_by_label[c.number_label]
            if id(p) not in used:
                used.add(id(p))
                label_match[id(c)] = p

    # Pass 2: positional fallback consumes remaining prior clauses in order.
    remaining_prev = [p for p in prev if id(p) not in used]
    fallback_iter = iter(remaining_prev)

    pairs: list[AlignmentPair] = []
    for c in curr:
        if id(c) in label_match:
            pairs.append(AlignmentPair(prev=label_match[id(c)], curr=c))
        else:
            p = next(fallback_iter, None)
            if p is not None:
                used.add(id(p))
            pairs.append(AlignmentPair(prev=p, curr=c))

    # Remaining prior clauses were never paired -> removed.
    for p in remaining_prev:
        if id(p) not in used:
            pairs.append(AlignmentPair(prev=p, curr=None))

    return pairs
