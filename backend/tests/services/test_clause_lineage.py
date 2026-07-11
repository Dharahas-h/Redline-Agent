"""Clause lineage query (Slice 6).

The cross-round lineage of a clause is the chain of aligned clauses across every
round — how a single clause evolved over the whole negotiation. The chain is
walked over the persisted ``ClauseLineage`` links, so it follows human alignment
overrides where present (decision #5).
"""

from redline_agent.domain import ChangeType
from redline_agent.infra.embedder import FakeEmbedder
from redline_agent.infra.llm.interpreter import FakeInterpreter
from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import AlignmentLink, RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx

# The Payment clause is renegotiated across three rounds; the Term clause is
# untouched. Numbered clauses align structurally, so the chain is unambiguous.
ROUND_1 = make_docx(["1. Payment", "Buyer pays in 30 days.", "2. Term", "One year."])
ROUND_2 = make_docx(["1. Payment", "Buyer pays in 45 days.", "2. Term", "One year."])
ROUND_3 = make_docx(["1. Payment", "Buyer pays in 60 days.", "2. Term", "One year."])


def _service(session_factory, blob_store):
    return RoundService(
        session_factory,
        blob_store,
        FakeInterpreter(summary="Machine-generated summary."),
        FakeEmbedder(),
        None,
    )


async def _upload(rounds, negotiation_id, party, data):
    r = await rounds.create_round(negotiation_id, party, "round.docx", data, TENANT)
    await rounds.process_round(r.id, TENANT)
    return r


async def _payment_clause_id(feed, round_id):
    """The current clause id of the Payment change in ``round_id``'s feed."""
    changes = await feed.feed(round_id, TENANT)
    change = next(c for c in changes if "days" in (c.raw_after or ""))
    return change.curr_clause_id


async def test_lineage_traces_a_clause_across_every_round(session_factory, blob_store):
    rounds = _service(session_factory, blob_store)
    feed = ChangeQueryService(session_factory)
    neg = await NegotiationService(session_factory).create("M", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    await _upload(rounds, neg.id, "Seller", ROUND_2)
    r3 = await _upload(rounds, neg.id, "Buyer", ROUND_3)

    curr_clause_id = await _payment_clause_id(feed, r3.id)
    result = await feed.clause_lineage(curr_clause_id, TENANT)

    assert result is not None
    assert result.clause_id == curr_clause_id
    assert result.negotiation_id == neg.id

    # One entry per round, in round order, tracing the Payment clause's text.
    assert [e.round.round_no for e in result.entries] == [1, 2, 3]
    assert "30 days" in result.entries[0].clause.text
    assert "45 days" in result.entries[1].clause.text
    assert "60 days" in result.entries[2].clause.text
    assert result.entries[0].clause.number_label == "1"

    # The first round has no prior, so no change into it; later rounds each carry
    # the modification that produced them.
    assert result.entries[0].change is None
    assert result.entries[1].change is not None
    assert result.entries[1].change.change_type is ChangeType.MODIFIED
    assert "45 days" in result.entries[1].change.raw_after
    assert result.entries[2].change.change_type is ChangeType.MODIFIED
    assert "60 days" in result.entries[2].change.raw_after


async def test_lineage_follows_a_human_override(session_factory, blob_store):
    rounds = _service(session_factory, blob_store)
    feed = ChangeQueryService(session_factory)
    neg = await NegotiationService(session_factory).create("M", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    curr_clause_id = await _payment_clause_id(feed, r2.id)
    before = await feed.clause_lineage(curr_clause_id, TENANT)
    # Before the override the Payment clause is aligned back to round 1.
    assert [e.round.round_no for e in before.entries] == [1, 2]
    round_1_clause_id = before.entries[0].clause.id

    # The user says the round-2 Payment clause is actually new: unlink its prior.
    await rounds.override_alignment(
        r2.id,
        TENANT,
        [AlignmentLink(curr_clause_id=curr_clause_id, prev_clause_id=None)],
    )

    # The lineage now follows the correction: the chain is severed, so the
    # round-2 clause stands alone and reads as an addition.
    after = await feed.clause_lineage(curr_clause_id, TENANT)
    assert [e.round.round_no for e in after.entries] == [2]
    assert after.entries[0].change.change_type is ChangeType.ADDED

    # ...and the round-1 clause no longer traces forward to round 2.
    from_round_1 = await feed.clause_lineage(round_1_clause_id, TENANT)
    assert [e.round.round_no for e in from_round_1.entries] == [1]


async def test_lineage_of_unknown_clause_is_none(session_factory, blob_store):
    feed = ChangeQueryService(session_factory)
    assert await feed.clause_lineage(999_999, TENANT) is None
