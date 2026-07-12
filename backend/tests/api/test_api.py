"""API seam: behavioral tests per route via httpx.AsyncClient."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import StaticPool

from redline_agent.config import Settings
from redline_agent.infra.blob_store import InMemoryBlobStore
from redline_agent.main import create_app
from redline_agent.repositories.orm import Base
from tests.fixtures.docx_builder import make_docx

ROUND_1 = make_docx(["1. Payment", "Buyer pays in 30 days.", "2. Term", "One year."])
ROUND_2 = make_docx(["1. Payment", "Buyer pays in 45 days.", "2. Term", "One year."])


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app = create_app(
        settings=Settings(_env_file=None, default_tenant_id="test"),
        blob_store=InMemoryBlobStore(),
        engine=engine,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


async def _upload(client, negotiation_id, party, data, name="round.docx"):
    return await client.post(
        f"/negotiations/{negotiation_id}/rounds",
        data={"submitted_by_party": party},
        files={"file": (name, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
    )


async def test_create_and_list_negotiations(client):
    resp = await client.post(
        "/negotiations", json={"title": "Acme MSA", "represented_party": "Buyer"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Acme MSA"
    assert body["represented_party"] == "Buyer"

    listing = await client.get("/negotiations")
    assert listing.status_code == 200
    assert [n["id"] for n in listing.json()] == [body["id"]]

    detail = await client.get(f"/negotiations/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["rounds"] == []


async def test_missing_negotiation_returns_404(client):
    assert (await client.get("/negotiations/999")).status_code == 404


async def test_upload_requires_docx(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    resp = await client.post(
        f"/negotiations/{neg['id']}/rounds",
        data={"submitted_by_party": "Buyer"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_two_rounds_and_see_changes(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()

    r1 = await _upload(client, neg["id"], "Buyer", ROUND_1)
    assert r1.status_code == 202
    assert r1.json()["round_no"] == 1

    r2 = await _upload(client, neg["id"], "Seller", ROUND_2)
    assert r2.status_code == 202
    round2_id = r2.json()["id"]

    feed = await client.get(f"/rounds/{round2_id}/changes")
    assert feed.status_code == 200
    payload = feed.json()
    assert payload["status"] == "ready"
    types = [c["change_type"] for c in payload["changes"]]
    assert types == ["modified"]
    change = payload["changes"][0]
    assert "30 days" in change["raw_before"]
    assert "45 days" in change["raw_after"]

    # single-change endpoint
    single = await client.get(f"/changes/{change['id']}")
    assert single.status_code == 200
    assert single.json()["id"] == change["id"]


DEFS_1 = make_docx(
    [
        "1. Definitions",
        '"Confidential Information" means non-public data disclosed orally.',
        "2. Obligations",
        "Each party shall protect Confidential Information.",
    ]
)
DEFS_2 = make_docx(
    [
        "1. Definitions",
        '"Confidential Information" means non-public data disclosed in writing.',
        "2. Obligations",
        "Each party shall protect Confidential Information.",
    ]
)
TABLE_1 = make_docx(
    ["1. Pricing", "See the schedule below."],
    tables=[[["Item", "Price"], ["Widget", "$10"]]],
)
TABLE_2 = make_docx(
    ["1. Pricing", "See the schedule below."],
    tables=[[["Item", "Price"], ["Widget", "$15"]]],
)


async def test_feed_surfaces_structural_alerts(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "NDA", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", DEFS_1)
    r2 = await _upload(client, neg["id"], "Seller", DEFS_2)
    round2_id = r2.json()["id"]

    payload = (await client.get(f"/rounds/{round2_id}/changes")).json()
    (alert,) = payload["alerts"]
    assert alert["alert_type"] == "definition_changed"
    assert alert["subject"] == "Confidential Information"
    assert alert["affected_clause_count"] == 1
    assert "Confidential Information" in alert["detail"]


async def test_feed_surfaces_table_alert_even_with_no_changes(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "MSA", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", TABLE_1)
    r2 = await _upload(client, neg["id"], "Seller", TABLE_2)
    round2_id = r2.json()["id"]

    payload = (await client.get(f"/rounds/{round2_id}/changes")).json()
    # Clause text is identical, so no change cards — but the table alert stands.
    assert payload["changes"] == []
    (alert,) = payload["alerts"]
    assert alert["alert_type"] == "table_changed"
    assert "review manually" in alert["detail"]


async def test_feed_surfaces_interpretation_and_filters_by_materiality(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    r2 = await _upload(client, neg["id"], "Seller", ROUND_2)
    round2_id = r2.json()["id"]

    payload = (await client.get(f"/rounds/{round2_id}/changes")).json()
    change = payload["changes"][0]
    assert change["summary"] is not None
    assert change["materiality"] == "substantive"

    # Hiding cosmetic keeps the substantive change...
    substantive = (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"materiality": "substantive"}
        )
    ).json()
    assert len(substantive["changes"]) == 1
    # ...and filtering to cosmetic hides it.
    cosmetic = (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"materiality": "cosmetic"}
        )
    ).json()
    assert cosmetic["changes"] == []


@pytest_asyncio.fixture
async def annotating_client():
    """A client whose interpreter tags every material change, so favored-party,
    category, and risk filters have something to bite on."""
    from redline_agent.domain import Category, FavoredParty, Materiality
    from redline_agent.infra.llm.interpreter import FakeInterpreter

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app = create_app(
        settings=Settings(_env_file=None, default_tenant_id="test"),
        blob_store=InMemoryBlobStore(),
        engine=engine,
        interpreter=FakeInterpreter(
            summary="Payment window extended.",
            materiality=Materiality.SUBSTANTIVE,
            category=Category.PAYMENT,
            favored_party=FavoredParty.COUNTERPARTY,
            risk_flag="For attorney review: payment terms shifted.",
        ),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    await engine.dispose()


async def test_feed_exposes_and_filters_favored_party_category_and_risk(
    annotating_client,
):
    client = annotating_client
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    r2 = await _upload(client, neg["id"], "Seller", ROUND_2)
    round2_id = r2.json()["id"]

    payload = (await client.get(f"/rounds/{round2_id}/changes")).json()
    change = payload["changes"][0]
    assert change["favored_party"] == "counterparty"
    assert change["category"] == "payment"
    assert change["risk_flag"] == "For attorney review: payment terms shifted."

    # Each filter narrows the feed.
    assert (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"favored_party": "counterparty"}
        )
    ).json()["changes"]
    assert not (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"favored_party": "represented"}
        )
    ).json()["changes"]
    assert (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"category": "payment"}
        )
    ).json()["changes"]
    assert not (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"category": "liability"}
        )
    ).json()["changes"]
    assert (
        await client.get(
            f"/rounds/{round2_id}/changes", params={"risk": "true"}
        )
    ).json()["changes"]


async def test_rounds_listed_for_negotiation(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    rounds = await client.get(f"/negotiations/{neg['id']}/rounds")
    assert rounds.status_code == 200
    assert [r["round_no"] for r in rounds.json()] == [1]


async def test_feed_missing_round_returns_404(client):
    assert (await client.get("/rounds/999/changes")).status_code == 404


# Unlabeled clauses with differing headings -> alignment is embedding-only and
# ambiguous, so the match is flagged low-confidence.
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


async def test_feed_flags_low_confidence_matches(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", AMBIG_1)
    r2 = await _upload(client, neg["id"], "Seller", AMBIG_2)
    round2_id = r2.json()["id"]

    payload = (await client.get(f"/rounds/{round2_id}/changes")).json()
    flagged = [c for c in payload["changes"] if c["low_confidence"]]
    assert flagged, "an uncertain embedding match should be flagged"
    assert flagged[0]["alignment_method"] == "embedding"
    assert flagged[0]["overridden"] is False


async def test_patch_alignment_override_regenerates_feed(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    r2 = await _upload(client, neg["id"], "Seller", ROUND_2)
    round2_id = r2.json()["id"]

    feed = (await client.get(f"/rounds/{round2_id}/changes")).json()
    modified = next(c for c in feed["changes"] if c["change_type"] == "modified")

    resp = await client.patch(
        f"/rounds/{round2_id}/alignment",
        json={
            "links": [
                {"curr_clause_id": modified["curr_clause_id"], "prev_clause_id": None}
            ]
        },
    )
    assert resp.status_code == 200
    types = sorted(c["change_type"] for c in resp.json()["changes"])
    assert types == ["added", "removed"]

    # The regenerated match is marked as a human override.
    refetched = (await client.get(f"/rounds/{round2_id}/changes")).json()
    added = next(c for c in refetched["changes"] if c["change_type"] == "added")
    assert added["overridden"] is True
    assert added["alignment_method"] == "override"


ROUND_3 = make_docx(["1. Payment", "Buyer pays in 60 days.", "2. Term", "One year."])


async def test_clause_lineage_traces_the_clause_across_rounds(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    await _upload(client, neg["id"], "Seller", ROUND_2)
    r3 = await _upload(client, neg["id"], "Buyer", ROUND_3)
    round3_id = r3.json()["id"]

    feed = (await client.get(f"/rounds/{round3_id}/changes")).json()
    payment = next(c for c in feed["changes"] if "60 days" in (c["raw_after"] or ""))

    lineage = await client.get(f"/clauses/{payment['curr_clause_id']}/lineage")
    assert lineage.status_code == 200
    body = lineage.json()
    assert body["clause_id"] == payment["curr_clause_id"]
    assert [e["round_no"] for e in body["entries"]] == [1, 2, 3]
    assert "30 days" in body["entries"][0]["text"]
    assert "60 days" in body["entries"][2]["text"]
    # The first round has no change into it; later rounds carry the modification.
    assert body["entries"][0]["change"] is None
    assert body["entries"][2]["change"]["change_type"] == "modified"


async def test_clause_lineage_unknown_clause_returns_404(client):
    assert (await client.get("/clauses/999999/lineage")).status_code == 404


async def test_patch_alignment_unknown_round_returns_404(client):
    resp = await client.patch(
        "/rounds/999/alignment", json={"links": []}
    )
    assert resp.status_code == 404


async def test_patch_alignment_rejects_foreign_clause(client):
    neg = (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    r2 = await _upload(client, neg["id"], "Seller", ROUND_2)
    round2_id = r2.json()["id"]

    resp = await client.patch(
        f"/rounds/{round2_id}/alignment",
        json={"links": [{"curr_clause_id": 999999, "prev_clause_id": None}]},
    )
    assert resp.status_code == 400
