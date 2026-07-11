"""Change-feed query service.

Serves the clause-centric change feed for a round. Filters are additive; in
this slice only materiality is meaningful (interpretation columns are
nullable), but the filter surface is established here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import Change, Round
from redline_agent.repositories.repos import ChangeRepository, RoundRepository


@dataclass
class ChangeFilters:
    materiality: str | None = None
    category: str | None = None
    favored_party: str | None = None
    risk: bool | None = None


class ChangeQueryService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_round(self, round_id: int, tenant_id: str) -> Round | None:
        async with self._session_factory() as session:
            return await RoundRepository(session).get(round_id, tenant_id)

    async def feed(
        self, round_id: int, tenant_id: str, filters: ChangeFilters | None = None
    ) -> list[Change]:
        filters = filters or ChangeFilters()
        async with self._session_factory() as session:
            changes = await ChangeRepository(session).list_for_round(
                round_id, tenant_id
            )
        return [c for c in changes if _matches(c, filters)]

    async def get(self, change_id: int, tenant_id: str) -> Change | None:
        async with self._session_factory() as session:
            return await ChangeRepository(session).get(change_id, tenant_id)


def _matches(change: Change, filters: ChangeFilters) -> bool:
    if filters.materiality is not None:
        value = change.materiality.value if change.materiality else None
        if value != filters.materiality:
            return False
    if filters.category is not None:
        value = change.category.value if change.category else None
        if value != filters.category:
            return False
    if filters.favored_party is not None:
        value = change.favored_party.value if change.favored_party else None
        if value != filters.favored_party:
            return False
    if filters.risk is not None and bool(change.risk_flag) != filters.risk:
        return False
    return True
