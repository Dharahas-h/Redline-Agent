"""Core invariant: persisted changes == exactly what the deterministic differ
produces.

Decision #1: nothing may invent, add, or drop changes. Here we drive the full
RoundService pipeline, then independently recompute the differ output from the
persisted clauses and assert the two sets are identical. The interpreter (added
in a later slice) will be re-checked against this same invariant with a
garbage-returning fake.
"""

import pytest

from redline_agent.pipeline.aligner import align_positional
from redline_agent.pipeline.differ import diff_pairs
from redline_agent.repositories.repos import ClauseRepository, RoundRepository
from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx


def _key(change_type, before, after):
    return (change_type, before, after)


async def test_persisted_changes_equal_differ_output(session_factory, blob_store):
    negotiations = NegotiationService(session_factory)
    rounds = RoundService(session_factory, blob_store)
    feed = ChangeQueryService(session_factory)

    neg = await negotiations.create("Matter", "Buyer", TENANT)
    r1 = await rounds.create_round(
        neg.id, "Buyer", "r1.docx", make_docx(["1. A", "alpha", "2. B", "beta"]), TENANT
    )
    await rounds.process_round(r1.id, TENANT)
    r2 = await rounds.create_round(
        neg.id, "Seller", "r2.docx",
        make_docx(["1. A", "alpha changed", "2. B", "beta", "3. C", "gamma"]),
        TENANT,
    )
    await rounds.process_round(r2.id, TENANT)

    # Independently recompute what the differ says, from persisted clauses.
    async with session_factory() as session:
        clause_repo = ClauseRepository(session)
        round_repo = RoundRepository(session)
        prior = await round_repo.prior_round(neg.id, r2.round_no, TENANT)
        prev_clauses = await clause_repo.list_for_round(prior.id, TENANT)
        curr_clauses = await clause_repo.list_for_round(r2.id, TENANT)
    expected = {
        _key(d.change_type, d.raw_before, d.raw_after)
        for d in diff_pairs(align_positional(prev_clauses, curr_clauses))
    }

    persisted = {
        _key(c.change_type, c.raw_before, c.raw_after)
        for c in await feed.feed(r2.id, TENANT)
    }

    assert persisted == expected
    assert len(persisted) == len(await feed.feed(r2.id, TENANT))  # no dupes
