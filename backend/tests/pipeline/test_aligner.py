"""Positional aligner: pair prior-round clauses to current-round clauses."""

from redline_agent.domain import Clause
from redline_agent.pipeline.aligner import align_positional


def _clause(ordinal, text, number_label=None, cid=None):
    return Clause(
        round_id=1,
        ordinal=ordinal,
        text=text,
        tenant_id="t1",
        number_label=number_label,
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
