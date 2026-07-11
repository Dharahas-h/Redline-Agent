"""Aligner: pair prior-round clauses to current-round clauses.

Positional alignment (Slice 1) is the no-embedder fallback; the embedding +
structural aligner with LLM adjudication (Slice 5) is exercised with a
deterministic ``FakeEmbedder`` and ``FakeAdjudicator`` so no test hits the
network.
"""

import pytest

from redline_agent.domain import AlignMethod, Clause
from redline_agent.infra.embedder import FakeEmbedder
from redline_agent.infra.llm.adjudicator import FakeAdjudicator
from redline_agent.pipeline.aligner import (
    CONF_AMBIGUOUS,
    CONF_EMBEDDING,
    CONF_STRUCTURAL,
    align,
    align_positional,
    is_low_confidence,
)


def _clause(ordinal, text, number_label=None, heading=None, cid=None):
    return Clause(
        round_id=1,
        ordinal=ordinal,
        text=text,
        tenant_id="t1",
        number_label=number_label,
        heading=heading,
        id=cid,
    )


def test_pairs_by_number_label():
    prev = [_clause(0, "1. A", "1", cid=10), _clause(1, "2. B", "2", cid=11)]
    curr = [_clause(0, "2. B changed", "2", cid=20), _clause(1, "1. A", "1", cid=21)]
    pairs = align_positional(prev, curr)
    by_curr = {p.curr.id: p.prev.id for p in pairs if p.curr and p.prev}
    assert by_curr == {20: 11, 21: 10}


def test_added_clause_has_no_prev():
    prev = [_clause(0, "1. A", "1", cid=10)]
    curr = [_clause(0, "1. A", "1", cid=20), _clause(1, "2. New", "2", cid=21)]
    pairs = align_positional(prev, curr)
    added = [p for p in pairs if p.prev is None]
    assert len(added) == 1 and added[0].curr.id == 21


def test_removed_clause_has_no_curr():
    prev = [_clause(0, "1. A", "1", cid=10), _clause(1, "2. B", "2", cid=11)]
    curr = [_clause(0, "1. A", "1", cid=20)]
    pairs = align_positional(prev, curr)
    removed = [p for p in pairs if p.curr is None]
    assert len(removed) == 1 and removed[0].prev.id == 11


def test_falls_back_to_ordinal_when_labels_absent():
    prev = [_clause(0, "Alpha", cid=10), _clause(1, "Beta", cid=11)]
    curr = [_clause(0, "Alpha edited", cid=20), _clause(1, "Beta", cid=21)]
    pairs = align_positional(prev, curr)
    by_curr = {p.curr.id: (p.prev.id if p.prev else None) for p in pairs if p.curr}
    assert by_curr == {20: 10, 21: 11}


# --- Embedding + structural aligner (Slice 5) ------------------------------


async def test_structural_match_wins_and_is_full_confidence():
    # Same clause number across rounds -> a full-confidence structural match,
    # regardless of how the wording changed.
    prev = [_clause(0, "Buyer pays in 30 days.", number_label="1", cid=10)]
    curr = [_clause(0, "Buyer pays in 45 days.", number_label="1", cid=20)]

    (pair, *_), = (await align(prev, curr, FakeEmbedder()),)
    assert pair.prev.id == 10 and pair.curr.id == 20
    assert pair.align_method is AlignMethod.HEADING
    assert pair.confidence == CONF_STRUCTURAL
    assert not is_low_confidence(pair.confidence)


async def test_confident_embedding_match_when_no_numbers():
    # Unlabeled clauses: the clearly-most-similar prior clause is a confident
    # embedding match; the unrelated prior clause is left as removed.
    prev = [
        _clause(0, "Buyer shall pay within 30 days", cid=10),
        _clause(1, "Either party may terminate for convenience", cid=11),
    ]
    curr = [_clause(0, "Buyer shall pay within 45 days", cid=20)]

    pairs = await align(prev, curr, FakeEmbedder())
    paired = next(p for p in pairs if p.curr and p.curr.id == 20)
    assert paired.prev.id == 10
    assert paired.align_method is AlignMethod.EMBEDDING
    assert paired.confidence == CONF_EMBEDDING
    assert not is_low_confidence(paired.confidence)
    removed = [p for p in pairs if p.curr is None]
    assert [p.prev.id for p in removed] == [11]


async def test_dissimilar_clause_is_treated_as_added():
    prev = [_clause(0, "Confidential information stays secret", cid=10)]
    curr = [_clause(0, "Governing law is New York", cid=20)]

    pairs = await align(prev, curr, FakeEmbedder())
    added = next(p for p in pairs if p.curr and p.curr.id == 20)
    assert added.prev is None


async def test_ambiguous_match_without_adjudicator_is_low_confidence():
    # Two prior clauses are equally similar to the current one (same overlap):
    # ambiguous. With no adjudicator, the aligner still guesses but flags it.
    prev = [
        _clause(0, "alpha beta gamma epsilon", cid=10),
        _clause(1, "alpha beta gamma omega", cid=11),
    ]
    curr = [_clause(0, "alpha beta gamma delta", cid=20)]

    pairs = await align(prev, curr, FakeEmbedder(), adjudicator=None)
    paired = next(p for p in pairs if p.curr and p.curr.id == 20)
    assert paired.prev is not None
    assert paired.align_method is AlignMethod.EMBEDDING
    assert paired.confidence == CONF_AMBIGUOUS
    assert is_low_confidence(paired.confidence)


async def test_ambiguous_match_falls_back_to_llm_adjudicator():
    prev = [
        _clause(0, "alpha beta gamma epsilon", cid=10),
        _clause(1, "alpha beta gamma omega", cid=11),
    ]
    curr = [_clause(0, "alpha beta gamma delta", cid=20)]
    adjudicator = FakeAdjudicator(choice=1, confidence=0.55)

    pairs = await align(prev, curr, FakeEmbedder(), adjudicator=adjudicator)
    paired = next(p for p in pairs if p.curr and p.curr.id == 20)
    assert adjudicator.calls == 1
    assert paired.align_method is AlignMethod.LLM
    assert paired.prev.id == 11  # the candidate the adjudicator chose
    assert paired.confidence == 0.55
    assert is_low_confidence(paired.confidence)


async def test_adjudicator_can_declare_a_new_clause():
    prev = [
        _clause(0, "alpha beta gamma epsilon", cid=10),
        _clause(1, "alpha beta gamma omega", cid=11),
    ]
    curr = [_clause(0, "alpha beta gamma delta", cid=20)]
    adjudicator = FakeAdjudicator(choice=None, confidence=0.4)

    pairs = await align(prev, curr, FakeEmbedder(), adjudicator=adjudicator)
    paired = next(p for p in pairs if p.curr and p.curr.id == 20)
    assert paired.prev is None
    assert paired.align_method is AlignMethod.LLM
