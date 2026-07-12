"""API seam: export routes via httpx.AsyncClient.

Uploads two rounds, generates a latest-vs-prior redline, and downloads it —
asserting the download is a valid tracked-changes ``.docx``.
"""

import io
import zipfile

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

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

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
        files={
            "file": (
                name,
                data,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )


async def _new_negotiation(client):
    return (
        await client.post(
            "/negotiations", json={"title": "M", "represented_party": "Buyer"}
        )
    ).json()


async def test_export_generates_and_downloads_redline(client):
    neg = await _new_negotiation(client)
    await _upload(client, neg["id"], "Buyer", ROUND_1)
    await _upload(client, neg["id"], "Seller", ROUND_2)

    created = await client.post(f"/negotiations/{neg['id']}/export")
    assert created.status_code == 201
    export = created.json()
    assert export["negotiation_id"] == neg["id"]

    download = await client.get(f"/exports/{export['id']}")
    assert download.status_code == 200
    assert (
        download.headers["content-type"]
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

    with zipfile.ZipFile(io.BytesIO(download.content)) as zf:
        xml = zf.read("word/document.xml").decode()
    # Latest-vs-prior redline: the 30 -> 45 edit is marked and attributed to the
    # party who submitted the latest round.
    assert "45" in xml
    assert 'w:author="Seller"' in xml or f'{{{W}}}author' in xml


async def test_export_requires_two_rounds(client):
    neg = await _new_negotiation(client)
    await _upload(client, neg["id"], "Buyer", ROUND_1)

    resp = await client.post(f"/negotiations/{neg['id']}/export")
    assert resp.status_code == 400


async def test_export_missing_negotiation_returns_404(client):
    assert (await client.post("/negotiations/999/export")).status_code == 404


async def test_download_missing_export_returns_404(client):
    assert (await client.get("/exports/999")).status_code == 404
