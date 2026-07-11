"""Aligner stage.

Matches each current-round clause to its counterpart in the prior round despite
renumbering, splits, merges, or moves. Alignment quality gates interpretation
quality and the lineage view, so the pairing is layered, cheapest-signal-first:

1. **Structural** — exact clause-number or heading match (``HEADING`` method,
   full confidence). This is the strongest signal and is tried first.
2. **Embedding** — cosine similarity of clause embeddings (``EMBEDDING``). A
   clearly-best, high-similarity candidate is a confident match.
3. **LLM adjudication** — a genuinely ambiguous case (no clear winner) is handed
   to the ``AlignmentAdjudicator`` (``LLM``); if none is configured the best
   embedding candidate is taken but flagged low-confidence for human review.

Each pairing records its similarity, confidence, and method so the feed can flag
uncertain matches (decision #5, the human-in-the-loop trust model). The
adjudicator only resolves ambiguity the pipeline surfaced — it never invents a
change; the differ downstream remains the sole authority on what changed
(decision #1).

``align_positional`` is retained as the no-embedder fallback (Slice 1 behaviour).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from redline_agent.domain import AlignMethod, Clause
from redline_agent.infra.embedder import Embedder
from redline_agent.infra.llm.adjudicator import (
    AdjudicationRequest,
    AlignmentAdjudicator,
)

# Similarity above which a clearly-best candidate is a confident embedding match.
SIM_HIGH = 0.75
# Similarity below which the best candidate is too weak to be a match at all.
SIM_LOW = 0.35
# The best candidate must beat the runner-up by this margin to be unambiguous.
MARGIN = 0.10

# Confidence recorded per alignment method.
CONF_STRUCTURAL = 1.0
CONF_EMBEDDING = 0.9
CONF_AMBIGUOUS = 0.5

# Pairings at or below this confidence are surfaced as low-confidence.
LOW_CONFIDENCE = 0.7
# Candidates handed to the LLM adjudicator for one ambiguous clause.
_MAX_CANDIDATES = 5


def is_low_confidence(confidence: float | None) -> bool:
    """Whether a pairing should be flagged for human review."""
    return confidence is not None and confidence < LOW_CONFIDENCE


@dataclass
class AlignmentPair:
    """A prior/current clause pairing. Either side may be None."""

    prev: Clause | None
    curr: Clause | None
    align_method: AlignMethod = AlignMethod.POSITIONAL
    similarity: float | None = None
    confidence: float = 1.0


def _cosine(a: list[float] | None, b: list[float] | None) -> float:
    if not a or not b:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


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


def _structural_key(clause: Clause) -> tuple[str | None, str | None]:
    label = clause.number_label
    heading = (clause.heading or "").strip().lower() or None
    return label, heading


async def align(
    prev: list[Clause],
    curr: list[Clause],
    embedder: Embedder,
    adjudicator: AlignmentAdjudicator | None = None,
) -> list[AlignmentPair]:
    """Align current clauses to prior clauses (structural → embedding → LLM).

    Returns one pairing per current clause (in current-round order), followed by
    a removed pairing for each prior clause left unmatched. Each pairing records
    the method, similarity, and confidence behind it.
    """
    if not curr:
        return [AlignmentPair(prev=p, curr=None) for p in prev]

    # Embed everything in one batch so vectors share a comparable space.
    vectors = await embedder.embed([c.text for c in prev + curr])
    vec_by_id = {id(c): vectors[i] for i, c in enumerate(prev + curr)}

    def sim(c1: Clause, c2: Clause) -> float:
        return _cosine(vec_by_id.get(id(c1)), vec_by_id.get(id(c2)))

    available: list[Clause] = list(prev)
    pairs_by_curr: dict[int, AlignmentPair] = {}

    # Pass 1: structural — exact number-label or heading match (unique).
    for c in curr:
        c_label, c_heading = _structural_key(c)
        if c_label is None and c_heading is None:
            continue
        matches = [
            p
            for p in available
            if (c_label is not None and p.number_label == c_label)
            or (c_heading is not None and _structural_key(p)[1] == c_heading)
        ]
        if len(matches) == 1:
            p = matches[0]
            available.remove(p)
            pairs_by_curr[id(c)] = AlignmentPair(
                prev=p,
                curr=c,
                align_method=AlignMethod.HEADING,
                similarity=sim(c, p),
                confidence=CONF_STRUCTURAL,
            )

    # Pass 2: embedding + LLM fallback for the rest, strongest matches first.
    remaining = [c for c in curr if id(c) not in pairs_by_curr]
    ranked = sorted(
        remaining,
        key=lambda c: max((sim(c, p) for p in available), default=0.0),
        reverse=True,
    )
    for c in ranked:
        scored = sorted(
            ((sim(c, p), p) for p in available), key=lambda t: t[0], reverse=True
        )
        best_sim = scored[0][0] if scored else 0.0
        second_sim = scored[1][0] if len(scored) > 1 else 0.0

        if not scored or best_sim < SIM_LOW:
            # Nothing plausible -> a genuine addition (prev=None).
            pairs_by_curr[id(c)] = AlignmentPair(
                prev=None,
                curr=c,
                align_method=AlignMethod.EMBEDDING,
                similarity=best_sim or None,
                confidence=CONF_EMBEDDING,
            )
            continue

        confident = best_sim >= SIM_HIGH and (best_sim - second_sim) >= MARGIN
        if confident:
            p = scored[0][1]
            available.remove(p)
            pairs_by_curr[id(c)] = AlignmentPair(
                prev=p,
                curr=c,
                align_method=AlignMethod.EMBEDDING,
                similarity=best_sim,
                confidence=CONF_EMBEDDING,
            )
            continue

        # Ambiguous: no clear winner. Ask the LLM adjudicator if we have one.
        candidates = [p for _, p in scored[:_MAX_CANDIDATES]]
        if adjudicator is not None:
            result = await adjudicator.adjudicate(
                AdjudicationRequest(
                    curr_text=c.text, candidates=[p.text for p in candidates]
                )
            )
            chosen = (
                candidates[result.choice]
                if result.choice is not None and 0 <= result.choice < len(candidates)
                else None
            )
            if chosen is not None:
                available.remove(chosen)
            pairs_by_curr[id(c)] = AlignmentPair(
                prev=chosen,
                curr=c,
                align_method=AlignMethod.LLM,
                similarity=best_sim,
                confidence=result.confidence,
            )
        else:
            # No adjudicator: take the best guess but flag it low-confidence.
            p = scored[0][1]
            available.remove(p)
            pairs_by_curr[id(c)] = AlignmentPair(
                prev=p,
                curr=c,
                align_method=AlignMethod.EMBEDDING,
                similarity=best_sim,
                confidence=CONF_AMBIGUOUS,
            )

    pairs = [pairs_by_curr[id(c)] for c in curr]
    pairs.extend(AlignmentPair(prev=p, curr=None) for p in available)
    return pairs
