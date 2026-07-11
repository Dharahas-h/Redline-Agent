"""Alignment override + regeneration, and low-confidence surfacing.

Slice 5: the embedding aligner flags uncertain matches, and a human can correct
a pairing (re-pair / split / merge) which regenerates the diff and
interpretation from the correction (decision #5).
"""

import pytest

from redline_agent.domain import AlignMethod, ChangeType
from redline_agent.infra.embedder import FakeEmbedder
from redline_agent.infra.llm.interpreter import FakeInterpreter
from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import AlignmentLink, RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx

# Numbered clauses -> confident structural alignment.
ROUND_1 = make_docx(["1. Payment", "Buyer pays in 30 days.", "2. Term", "One year."])
ROUND_2 = make_docx(["1. Payment", "Buyer pays in 45 days.", "2. Term", "One year."])

# Unlabeled clauses whose headings differ across rounds, so the current clause
# is only alignable by embedding and is genuinely ambiguous between two priors.
AMBIG_1 = make_docx(
    [
        "ALPHA ONE",
        "the party shall protect confidential information",
        "ALPHA TWO",
        "the party shall protect data and records",
    ]
)
AMBIG_2 = make_docx(
    [
        "BETA ONE",
        "the party shall protect confidential information and data and records",
    ]
)


def _service(session_factory, blob_store, adjudicator=None):
    return RoundService(
        session_factory,
        blob_store,
        FakeInterpreter(summary="Machine-generated summary."),
        FakeEmbedder(),
        adjudicator,
    )


async def _upload(rounds, negotiation_id, party, data):
    r = await rounds.create_round(negotiation_id, party, "round.docx", data, TENANT)
    await rounds.process_round(r.id, TENANT)
    return r


async def test_ambiguous_match_is_low_confidence_in_the_feed(
    session_factory, blob_store
):
    rounds = _service(session_factory, blob_store, adjudicator=None)
    feed = ChangeQueryService(session_factory)
    neg = await NegotiationService(session_factory).create("M", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", AMBIG_1)
    r2 = await _upload(rounds, neg.id, "Seller", AMBIG_2)

    alignment = await feed.alignment_for_round(r2.id, TENANT)
    # The single current clause was matched by embedding, not structure, and the
    # match is uncertain -> flagged low-confidence for human review.
    (link,) = alignment.values()
    assert link.align_method is AlignMethod.EMBEDDING
    assert link.confidence is not None and link.confidence < 0.7
    assert not link.overridden


async def test_override_repairs_a_pairing_and_regenerates_the_diff(
    session_factory, blob_store
):
    rounds = _service(session_factory, blob_store)
    feed = ChangeQueryService(session_factory)
    neg = await NegotiationService(session_factory).create("M", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    before = await feed.feed(r2.id, TENANT)
    modified = next(c for c in before if c.change_type is ChangeType.MODIFIED)

    # The user says the payment clause is actually new: unlink its prior match.
    round_ = await rounds.override_alignment(
        r2.id,
        TENANT,
        [AlignmentLink(curr_clause_id=modified.curr_clause_id, prev_clause_id=None)],
    )
    assert round_ is not None

    after = await feed.feed(r2.id, TENANT)
    by_type = sorted(c.change_type.value for c in after)
    # Unlinking turns one modification into an addition + a removal.
    assert by_type == ["added", "removed"]
    added = next(c for c in after if c.change_type is ChangeType.ADDED)
    assert "45 days" in added.raw_after
    assert added.summary is not None  # interpretation regenerated

    alignment = await feed.alignment_for_round(r2.id, TENANT)
    link = alignment[modified.curr_clause_id]
    assert link.overridden is True
    assert link.align_method is AlignMethod.OVERRIDE
    assert link.prev_clause_id is None


async def test_override_rejects_a_clause_from_another_round(
    session_factory, blob_store
):
    rounds = _service(session_factory, blob_store)
    neg = await NegotiationService(session_factory).create("M", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    with pytest.raises(ValueError):
        await rounds.override_alignment(
            r2.id,
            TENANT,
            [AlignmentLink(curr_clause_id=999_999, prev_clause_id=None)],
        )


async def test_override_on_unknown_round_returns_none(session_factory, blob_store):
    rounds = _service(session_factory, blob_store)
    assert await rounds.override_alignment(999, TENANT, []) is None
