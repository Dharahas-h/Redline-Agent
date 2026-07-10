"""Negotiation application service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import Negotiation, Round
from redline_agent.repositories.repos import (
    NegotiationRepository,
    RoundRepository,
)


class NegotiationService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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
