"""ChangeQueryService feed filters: favored-party, category, and risk.

The feed filter surface is additive. This slice makes category, favored-party,
and risk meaningful (issue 04). Filtering is exercised end to end through a
persisted round so it matches what the API serves.
"""

import pytest

from redline_agent.domain import Category, FavoredParty, Materiality
from redline_agent.infra.llm.interpreter import FakeInterpreter
from redline_agent.services.change_query import ChangeFilters, ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx

ROUND_1 = make_docx(["1. Payment", "Buyer shall pay within 30 days."])
ROUND_2 = make_docx(["1. Payment", "Buyer shall pay within 45 days."])


async def _feed_with(session_factory, blob_store, interp):
    negotiations = NegotiationService(session_factory)
    rounds = RoundService(session_factory, blob_store, interp)
    feed = ChangeQueryService(session_factory)
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    r1 = await rounds.create_round(neg.id, "Buyer", "r1.docx", ROUND_1, TENANT)
    await rounds.process_round(r1.id, TENANT)
    r2 = await rounds.create_round(neg.id, "Seller", "r2.docx", ROUND_2, TENANT)
    await rounds.process_round(r2.id, TENANT)
    return feed, r2


async def test_filter_by_favored_party(session_factory, blob_store):
    interp = FakeInterpreter(
        materiality=Materiality.SUBSTANTIVE,
        favored_party=FavoredParty.COUNTERPARTY,
    )
    feed, r2 = await _feed_with(session_factory, blob_store, interp)

    match = await feed.feed(
        r2.id, TENANT, ChangeFilters(favored_party="counterparty")
    )
    assert len(match) == 1
    miss = await feed.feed(
        r2.id, TENANT, ChangeFilters(favored_party="represented")
    )
    assert miss == []


async def test_filter_by_category(session_factory, blob_store):
    interp = FakeInterpreter(
        materiality=Materiality.SUBSTANTIVE, category=Category.PAYMENT
    )
    feed, r2 = await _feed_with(session_factory, blob_store, interp)

    assert len(await feed.feed(r2.id, TENANT, ChangeFilters(category="payment"))) == 1
    assert await feed.feed(r2.id, TENANT, ChangeFilters(category="liability")) == []


async def test_filter_by_risk_shows_only_flagged_changes(session_factory, blob_store):
    interp = FakeInterpreter(
        materiality=Materiality.SUBSTANTIVE,
        risk_flag="For attorney review: payment terms shifted.",
    )
    feed, r2 = await _feed_with(session_factory, blob_store, interp)

    flagged = await feed.feed(r2.id, TENANT, ChangeFilters(risk=True))
    assert len(flagged) == 1
    assert flagged[0].risk_flag


async def test_filter_by_risk_excludes_unflagged_changes(session_factory, blob_store):
    interp = FakeInterpreter(materiality=Materiality.SUBSTANTIVE, risk_flag=None)
    feed, r2 = await _feed_with(session_factory, blob_store, interp)

    assert await feed.feed(r2.id, TENANT, ChangeFilters(risk=True)) == []
