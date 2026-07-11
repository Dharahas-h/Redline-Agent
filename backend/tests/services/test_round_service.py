"""RoundService orchestration seam: fixture .docx -> persisted clauses/changes."""

import pytest

from redline_agent.domain import (
    Category,
    ChangeType,
    FavoredParty,
    Materiality,
    RoundStatus,
)
from redline_agent.infra.llm.interpreter import FakeInterpreter
from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx

ROUND_1 = make_docx(
    [
        "1. Payment",
        "Buyer shall pay within 30 days.",
        "2. Term",
        "This agreement lasts one year.",
    ]
)
ROUND_2 = make_docx(
    [
        "1. Payment",
        "Buyer shall pay within 45 days.",
        "2. Term",
        "This agreement lasts one year.",
        "3. Confidentiality",
        "Each party keeps secrets.",
    ]
)


@pytest.fixture
def services(session_factory, blob_store, interpreter):
    return (
        NegotiationService(session_factory),
        RoundService(session_factory, blob_store, interpreter),
        ChangeQueryService(session_factory),
    )


async def _upload(round_service, negotiation_id, party, data):
    r = await round_service.create_round(
        negotiation_id, party, "round.docx", data, TENANT
    )
    await round_service.process_round(r.id, TENANT)
    return r


async def test_round_starts_pending_then_becomes_ready(services):
    negotiations, rounds, _ = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)

    created = await rounds.create_round(
        neg.id, "Buyer", "r1.docx", ROUND_1, TENANT
    )
    assert created.status is RoundStatus.PENDING
    assert created.round_no == 1

    await rounds.process_round(created.id, TENANT)
    (fetched,) = await negotiations.list_rounds(neg.id, TENANT)
    assert fetched.status is RoundStatus.READY


async def test_second_round_produces_clause_centric_changes(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)

    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    changes = await feed.feed(r2.id, TENANT)
    by_type = {c.change_type for c in changes}
    assert by_type == {ChangeType.MODIFIED, ChangeType.ADDED}
    assert len(changes) == 2

    modified = next(c for c in changes if c.change_type is ChangeType.MODIFIED)
    assert "30 days" in modified.raw_before
    assert "45 days" in modified.raw_after

    added = next(c for c in changes if c.change_type is ChangeType.ADDED)
    assert added.raw_before is None
    assert "Confidentiality" in added.raw_after


async def test_material_changes_are_interpreted(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    changes = await feed.feed(r2.id, TENANT)
    for c in changes:
        assert c.summary is not None
        assert c.materiality is Materiality.SUBSTANTIVE
        assert c.interpretation_model == "fake"


async def test_changes_carry_favored_party_category_and_risk(session_factory, blob_store):
    # A dedicated interpreter so we can assert the extended annotation lands.
    interp = FakeInterpreter(
        summary="Payment window extended.",
        materiality=Materiality.SUBSTANTIVE,
        category=Category.PAYMENT,
        favored_party=FavoredParty.COUNTERPARTY,
        risk_flag="For attorney review: the payment window moved out.",
    )
    negotiations = NegotiationService(session_factory)
    rounds = RoundService(session_factory, blob_store, interp)
    feed = ChangeQueryService(session_factory)
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    changes = await feed.feed(r2.id, TENANT)
    material = [c for c in changes if c.materiality is Materiality.SUBSTANTIVE]
    assert material
    for c in material:
        assert c.category is Category.PAYMENT
        assert c.favored_party is FavoredParty.COUNTERPARTY
        assert c.risk_flag == "For attorney review: the payment window moved out."


async def test_interpreter_receives_the_negotiations_represented_party(
    session_factory, blob_store
):
    # Favored-party must be computed relative to the represented party captured
    # when the negotiation was created.
    interp = FakeInterpreter(favored_party=FavoredParty.REPRESENTED)
    negotiations = NegotiationService(session_factory)
    rounds = RoundService(session_factory, blob_store, interp)
    neg = await negotiations.create("Acme MSA", "Landlord", TENANT)
    await _upload(rounds, neg.id, "Landlord", ROUND_1)
    await _upload(rounds, neg.id, "Tenant", ROUND_2)

    assert interp.requests  # the interpreter was invoked on the material change
    assert all(r.represented_party == "Landlord" for r in interp.requests)


async def test_cosmetic_change_is_tagged_without_the_llm(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    # Round 2 differs from round 1 only by case + trailing punctuation -> cosmetic.
    cosmetic = make_docx(
        [
            "1. Payment",
            "Buyer shall pay within 30 days",
            "2. Term",
            "this agreement lasts one year.",
        ]
    )
    r2 = await _upload(rounds, neg.id, "Seller", cosmetic)

    changes = await feed.feed(r2.id, TENANT)
    assert changes  # the differ still detected the deltas
    assert all(c.materiality is Materiality.COSMETIC for c in changes)
    assert all(c.interpretation_model is None for c in changes)

    # And the materiality filter can hide them.
    from redline_agent.services.change_query import ChangeFilters

    visible = await feed.feed(
        r2.id, TENANT, ChangeFilters(materiality="substantive")
    )
    assert visible == []


async def test_first_round_has_no_changes(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    r1 = await _upload(rounds, neg.id, "Buyer", ROUND_1)
    assert await feed.feed(r1.id, TENANT) == []


async def test_tenant_isolation_hides_other_tenants_feed(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    assert await feed.feed(r2.id, "other-tenant") == []
