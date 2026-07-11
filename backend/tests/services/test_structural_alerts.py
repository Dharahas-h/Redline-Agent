"""Structural alerts through the RoundService seam: definition + table changes.

Alerts are surfaced alongside the feed but are not changes — the deterministic
differ still owns the change set (decision #1, #6).
"""

import pytest

from redline_agent.domain import AlertType
from redline_agent.services.change_query import ChangeQueryService
from redline_agent.services.negotiation import NegotiationService
from redline_agent.services.round_service import AlignmentLink, RoundService
from tests.conftest import TENANT
from tests.fixtures.docx_builder import make_docx

# Two rounds where a defined term is redefined and two other clauses cite it.
DEFS_1 = make_docx(
    [
        "1. Definitions",
        '"Confidential Information" means non-public data disclosed orally.',
        "2. Obligations",
        "Each party shall protect Confidential Information.",
        "3. Return",
        "Return all Confidential Information on termination.",
    ]
)
DEFS_2 = make_docx(
    [
        "1. Definitions",
        '"Confidential Information" means non-public data disclosed in writing.',
        "2. Obligations",
        "Each party shall protect Confidential Information.",
        "3. Return",
        "Return all Confidential Information on termination.",
    ]
)

# Two rounds whose only difference is a table cell — no clause text changes.
TABLE_1 = make_docx(
    ["1. Pricing", "See the schedule below."],
    tables=[[["Item", "Price"], ["Widget", "$10"]]],
)
TABLE_2 = make_docx(
    ["1. Pricing", "See the schedule below."],
    tables=[[["Item", "Price"], ["Widget", "$15"]]],
)


@pytest.fixture
def services(session_factory, blob_store, interpreter):
    return (
        NegotiationService(session_factory),
        RoundService(session_factory, blob_store, interpreter),
        ChangeQueryService(session_factory),
    )


async def _upload(rounds, negotiation_id, party, data):
    r = await rounds.create_round(negotiation_id, party, "r.docx", data, TENANT)
    await rounds.process_round(r.id, TENANT)
    return r


async def test_changed_definition_is_flagged_with_reference_count(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme NDA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", DEFS_1)
    r2 = await _upload(rounds, neg.id, "Seller", DEFS_2)

    (alert,) = await feed.structural_alerts(r2.id, TENANT)
    assert alert.alert_type is AlertType.DEFINITION_CHANGED
    assert alert.subject == "Confidential Information"
    assert alert.affected_clause_count == 2
    assert "Confidential Information" in alert.detail
    assert "2 clauses" in alert.detail


async def test_changed_table_is_flagged_for_manual_review(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme MSA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", TABLE_1)
    r2 = await _upload(rounds, neg.id, "Seller", TABLE_2)

    # The clause text is identical across rounds, so there is no change...
    assert await feed.feed(r2.id, TENANT) == []
    # ...yet the table edit is still surfaced as a manual-review alert.
    (alert,) = await feed.structural_alerts(r2.id, TENANT)
    assert alert.alert_type is AlertType.TABLE_CHANGED
    assert alert.affected_clause_count is None
    assert "review manually" in alert.detail


async def test_no_alerts_when_definitions_and_tables_are_stable(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme NDA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", DEFS_1)
    # Re-upload an identical body: same definition, no tables -> no alerts.
    r2 = await _upload(rounds, neg.id, "Seller", DEFS_1)
    assert await feed.structural_alerts(r2.id, TENANT) == []


async def test_first_round_has_no_alerts(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme NDA", "Buyer", TENANT)
    r1 = await _upload(rounds, neg.id, "Buyer", DEFS_1)
    assert await feed.structural_alerts(r1.id, TENANT) == []


async def test_alerts_regenerate_on_alignment_override(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme NDA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", DEFS_1)
    r2 = await _upload(rounds, neg.id, "Seller", DEFS_2)

    # An override re-runs the diff and alerts; the alert set stays consistent
    # (idempotent — not duplicated) rather than piling up.
    changes = await feed.feed(r2.id, TENANT)
    a_change = changes[0]
    await rounds.override_alignment(
        r2.id,
        TENANT,
        [AlignmentLink(curr_clause_id=a_change.curr_clause_id, prev_clause_id=None)],
    )
    alerts = await feed.structural_alerts(r2.id, TENANT)
    # Still exactly one definition alert; the override did not duplicate it.
    assert [a.alert_type for a in alerts] == [AlertType.DEFINITION_CHANGED]


async def test_tenant_isolation_hides_other_tenants_alerts(services):
    negotiations, rounds, feed = services
    neg = await negotiations.create("Acme NDA", "Buyer", TENANT)
    await _upload(rounds, neg.id, "Buyer", DEFS_1)
    r2 = await _upload(rounds, neg.id, "Seller", DEFS_2)
    assert await feed.structural_alerts(r2.id, "other-tenant") == []
