"""Export application service.

Generates a latest-vs-prior tracked-changes ``.docx`` for a negotiation by
handing the two most recent rounds' original blobs to the standalone
``redline()`` function, then storing the result in the blob store and recording
an ``Export`` row. The service is the only bridge between stored rounds and the
standalone export package — ``redline()`` itself imports nothing from here.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import Export
from redline_agent.infra.blob_store import BlobStore
from redline_agent.redline import redline
from redline_agent.repositories.repos import (
    ExportRepository,
    RoundRepository,
)


class NotEnoughRoundsError(Exception):
    """Raised when a negotiation has fewer than two rounds to redline."""


class ExportService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        blob_store: BlobStore,
    ) -> None:
        self._session_factory = session_factory
        self._blob_store = blob_store

    async def generate(self, negotiation_id: int, tenant_id: str) -> Export:
        """Redline the latest round against the prior; persist and return it."""
        async with self._session_factory() as session:
            rounds_repo = RoundRepository(session)
            rounds = await rounds_repo.list_for_negotiation(
                negotiation_id, tenant_id
            )
            if len(rounds) < 2:
                raise NotEnoughRoundsError(
                    "A redline needs at least two rounds (latest vs prior)."
                )
            prior, latest = rounds[-2], rounds[-1]

            prev_bytes = self._blob_store.get(prior.blob_uri)
            curr_bytes = self._blob_store.get(latest.blob_uri)
            date = (
                latest.created_at.isoformat()
                if latest.created_at is not None
                else "1970-01-01T00:00:00Z"
            )
            redlined = redline(
                prev_bytes,
                curr_bytes,
                author=latest.submitted_by_party,
                date=date,
            )

            filename = (
                f"redline-negotiation-{negotiation_id}"
                f"-round-{latest.round_no}-vs-{prior.round_no}.docx"
            )
            blob_uri = self._blob_store.put(
                f"{tenant_id}/{negotiation_id}/exports/{filename}", redlined
            )

            export = await ExportRepository(session).create(
                Export(
                    negotiation_id=negotiation_id,
                    from_round_id=prior.id,
                    to_round_id=latest.id,
                    tenant_id=tenant_id,
                    filename=filename,
                    blob_uri=blob_uri,
                )
            )
            await session.commit()
            return export

    async def get(self, export_id: int, tenant_id: str) -> Export | None:
        async with self._session_factory() as session:
            return await ExportRepository(session).get(export_id, tenant_id)

    def read_bytes(self, export: Export) -> bytes:
        return self._blob_store.get(export.blob_uri)
