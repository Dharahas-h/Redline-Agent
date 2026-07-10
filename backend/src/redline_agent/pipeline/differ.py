"""Differ stage.

Word/clause-level diff of aligned clause pairs. The differ is the sole
authority on which changes exist: an identical pair produces no change, and
nothing downstream may add to or remove from this set (decision #1).
"""

from __future__ import annotations

from dataclasses import dataclass

from redline_agent.domain import ChangeType, Clause
from redline_agent.pipeline.aligner import AlignmentPair


@dataclass
class DiffResult:
    """A detected change for one aligned pair, before it is bound to a round."""

    change_type: ChangeType
    prev_clause: Clause | None
    curr_clause: Clause | None
    raw_before: str | None
    raw_after: str | None


def diff_pairs(pairs: list[AlignmentPair]) -> list[DiffResult]:
    """Produce a DiffResult per changed pair; unchanged pairs are omitted."""
    results: list[DiffResult] = []
    for pair in pairs:
        prev, curr = pair.prev, pair.curr
        if prev is None and curr is not None:
            results.append(
                DiffResult(ChangeType.ADDED, None, curr, None, curr.text)
            )
        elif prev is not None and curr is None:
            results.append(
                DiffResult(ChangeType.REMOVED, prev, None, prev.text, None)
            )
        elif prev is not None and curr is not None:
            if prev.text != curr.text:
                results.append(
                    DiffResult(
                        ChangeType.MODIFIED, prev, curr, prev.text, curr.text
                    )
                )
    return results
