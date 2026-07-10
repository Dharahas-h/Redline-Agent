"""Differ: turn aligned clause pairs into detected changes."""

from redline_agent.domain import ChangeType, Clause
from redline_agent.pipeline.aligner import AlignmentPair
from redline_agent.pipeline.differ import diff_pairs


def _clause(text, cid):
    return Clause(round_id=1, ordinal=0, text=text, tenant_id="t1", id=cid)


def test_identical_clause_yields_no_change():
    pair = AlignmentPair(prev=_clause("same", 10), curr=_clause("same", 20))
    assert diff_pairs([pair]) == []


def test_modified_clause_yields_modified_change():
    pair = AlignmentPair(prev=_clause("pay in 30 days", 10), curr=_clause("pay in 45 days", 20))
    (change,) = diff_pairs([pair])
    assert change.change_type is ChangeType.MODIFIED
    assert change.raw_before == "pay in 30 days"
    assert change.raw_after == "pay in 45 days"
    assert change.prev_clause.id == 10 and change.curr_clause.id == 20


def test_added_clause_yields_added_change():
    pair = AlignmentPair(prev=None, curr=_clause("brand new", 20))
    (change,) = diff_pairs([pair])
    assert change.change_type is ChangeType.ADDED
    assert change.raw_before is None
    assert change.raw_after == "brand new"


def test_removed_clause_yields_removed_change():
    pair = AlignmentPair(prev=_clause("gone", 10), curr=None)
    (change,) = diff_pairs([pair])
    assert change.change_type is ChangeType.REMOVED
    assert change.raw_before == "gone"
    assert change.raw_after is None
