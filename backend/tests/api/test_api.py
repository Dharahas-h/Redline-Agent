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
        settings=Settings(default_tenant_id="test"),
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
