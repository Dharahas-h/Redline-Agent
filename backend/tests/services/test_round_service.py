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
from redline_agent.services.negotiation import (
    NegotiationNotDeletableError,
    NegotiationService,
)
from redline_agent.services.round_service import (
    RoundNotDeletableError,
    RoundService,
)
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


async def test_delete_latest_round_removes_rows_and_blob(services, blob_store):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)
    assert r2.blob_uri in blob_store._data or r2.blob_uri.split("://", 1)[-1] in blob_store._data

    ok = await rounds.delete_round(neg.id, r2.id, TENANT)
    assert ok is True

    remaining = await negotiations.list_rounds(neg.id, TENANT)
    assert [r.round_no for r in remaining] == [1]
    # The round's changes are gone with it.
    assert await feed.feed(r2.id, TENANT) == []
    # Its blob was removed from the store.
    assert r2.blob_uri.split("://", 1)[-1] not in blob_store._data


async def test_deleted_round_number_is_reused_on_reupload(services):
    negotiations, rounds, _ = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)
    assert r2.round_no == 2

    await rounds.delete_round(neg.id, r2.id, TENANT)
    r2b = await _upload(rounds, neg.id, "Seller", ROUND_2)
    assert r2b.round_no == 2


async def test_cannot_delete_non_latest_round(services):
    negotiations, rounds, _ = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    r1 = await _upload(rounds, neg.id, "Buyer", ROUND_1)
    await _upload(rounds, neg.id, "Seller", ROUND_2)

    with pytest.raises(RoundNotDeletableError):
        await rounds.delete_round(neg.id, r1.id, TENANT)


async def test_cannot_delete_round_that_is_still_processing(services):
    negotiations, rounds, _ = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    # create_round leaves the round PENDING (the pipeline has not run yet).
    pending = await rounds.create_round(neg.id, "Buyer", "r1.docx", ROUND_1, TENANT)
    assert pending.status is RoundStatus.PENDING

    with pytest.raises(RoundNotDeletableError):
        await rounds.delete_round(neg.id, pending.id, TENANT)


async def test_delete_round_unknown_or_foreign_tenant_returns_false(services):
    negotiations, rounds, _ = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    r1 = await _upload(rounds, neg.id, "Buyer", ROUND_1)

    assert await rounds.delete_round(neg.id, 999999, TENANT) is False
    assert await rounds.delete_round(neg.id, r1.id, "other-tenant") is False


async def test_delete_negotiation_cascades_rounds_and_blobs(
    session_factory, blob_store, interpreter
):
    negotiations = NegotiationService(session_factory, blob_store)
    rounds = RoundService(session_factory, blob_store, interpreter)
    feed = ChangeQueryService(session_factory)
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", ROUND_1)
    r2 = await _upload(rounds, neg.id, "Seller", ROUND_2)

    ok = await negotiations.delete(neg.id, TENANT)
    assert ok is True

    assert await negotiations.get(neg.id, TENANT) is None
    assert await negotiations.list_rounds(neg.id, TENANT) == []
    assert await feed.feed(r2.id, TENANT) == []
    # Every round blob is gone.
    assert blob_store._data == {}


async def test_delete_negotiation_blocked_while_round_processing(
    session_factory, blob_store, interpreter
):
    negotiations = NegotiationService(session_factory, blob_store)
    rounds = RoundService(session_factory, blob_store, interpreter)
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    # A round left PENDING (pipeline not run) must block the delete.
    await rounds.create_round(neg.id, "Buyer", "r1.docx", ROUND_1, TENANT)

    with pytest.raises(NegotiationNotDeletableError):
        await negotiations.delete(neg.id, TENANT)


async def test_delete_negotiation_unknown_or_foreign_tenant_returns_false(
    session_factory, blob_store
):
    negotiations = NegotiationService(session_factory, blob_store)
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)

    assert await negotiations.delete(999999, TENANT) is False
    assert await negotiations.delete(neg.id, "other-tenant") is False
