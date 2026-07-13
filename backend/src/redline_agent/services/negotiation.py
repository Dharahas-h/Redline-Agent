"""Negotiation application service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import Negotiation, Round, RoundStatus
from redline_agent.infra.blob_store import BlobStore
from redline_agent.repositories.repos import (
    NegotiationRepository,
    RoundRepository,
)
from redline_agent.services.round_service import delete_blobs, purge_round


class NegotiationNotDeletableError(Exception):
    """Raised when a negotiation cannot be deleted (a round is still processing)."""


class NegotiationService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        blob_store: BlobStore | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._blob_store = blob_store

    async def create(
        self, title: str, represented_party: str, tenant_id: str
    ) -> Negotiation:
        async with self._session_factory() as session:
            negotiation = await NegotiationRepository(session).create(
                Negotiation(
                    title=title,
                    represented_party=represented_party,
                    tenant_id=tenant_id,
                )
            )
            await session.commit()
            return negotiation

    async def list(self, tenant_id: str) -> list[Negotiation]:
        async with self._session_factory() as session:
            return await NegotiationRepository(session).list(tenant_id)

    async def get(self, negotiation_id: int, tenant_id: str) -> Negotiation | None:
        async with self._session_factory() as session:
            return await NegotiationRepository(session).get(
                negotiation_id, tenant_id
            )

    async def list_rounds(
        self, negotiation_id: int, tenant_id: str
    ) -> list[Round]:
        async with self._session_factory() as session:
            return await RoundRepository(session).list_for_negotiation(
                negotiation_id, tenant_id
            )

    async def delete(self, negotiation_id: int, tenant_id: str) -> bool:
        """Hard-delete a negotiation and every round beneath it (with blobs).

        Returns ``False`` if the negotiation is unknown for this tenant (router
        maps that to 404). Raises ``NegotiationNotDeletableError`` (mapped to
        409) if any round is still ``pending``/``processing``, so the delete
        cannot race the background pipeline.
        """
        async with self._session_factory() as session:
            negotiations = NegotiationRepository(session)
            if await negotiations.get(negotiation_id, tenant_id) is None:
                return False

            rounds = await RoundRepository(session).list_for_negotiation(
                negotiation_id, tenant_id
            )
            if any(
                r.status in (RoundStatus.PENDING, RoundStatus.PROCESSING)
                for r in rounds
            ):
                raise NegotiationNotDeletableError(
                    "A round is still processing; try again once it is ready."
                )

            blob_uris: list[str] = []
            for round_ in rounds:
                blob_uris.extend(await purge_round(session, round_, tenant_id))
            await negotiations.delete(negotiation_id, tenant_id)
            await session.commit()

        if self._blob_store is not None:
            delete_blobs(self._blob_store, blob_uris)
        return True
