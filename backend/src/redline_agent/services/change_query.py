"""Change-feed query service.

Serves the clause-centric change feed for a round. Filters are additive; in
this slice only materiality is meaningful (interpretation columns are
nullable), but the filter surface is established here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from redline_agent.domain import (
    Change,
    Clause,
    ClauseLineage,
    Round,
    StructuralAlert,
)
from redline_agent.repositories.repos import (
    ChangeRepository,
    ClauseLineageRepository,
    ClauseRepository,
    RoundRepository,
    StructuralAlertRepository,
)


@dataclass
class ChangeFilters:
    materiality: str | None = None
    category: str | None = None
    favored_party: str | None = None
    risk: bool | None = None


@dataclass
class LineageEntry:
    """One round's view of a clause in its cross-round lineage."""

    clause: Clause
    round: Round
    change: Change | None
    lineage: ClauseLineage | None


@dataclass
class ClauseLineageView:
    """A clause's full evolution across every round, in round order."""

    clause_id: int
    negotiation_id: int
    entries: list[LineageEntry]


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

    async def structural_alerts(
        self, round_id: int, tenant_id: str
    ) -> list[StructuralAlert]:
        """Structural alerts (definition/table changes) surfaced for the round.

        Distinct from the change feed — these annotate high-value structural
        events, not the deterministic change set (decision #1, #6).
        """
        async with self._session_factory() as session:
            return await StructuralAlertRepository(session).list_for_round(
                round_id, tenant_id
            )

    async def get(self, change_id: int, tenant_id: str) -> Change | None:
        async with self._session_factory() as session:
            return await ChangeRepository(session).get(change_id, tenant_id)

    async def alignment_for_round(
        self, round_id: int, tenant_id: str
    ) -> dict[int, ClauseLineage]:
        """Lineage links for the round, keyed by current clause id.

        Lets the feed flag low-confidence and overridden clause matches without
        the caller reaching into the repositories.
        """
        async with self._session_factory() as session:
            lineage = await ClauseLineageRepository(session).list_for_round(
                round_id, tenant_id
            )
        return {link.curr_clause_id: link for link in lineage}

    async def alignment_for_clause(
        self, curr_clause_id: int, tenant_id: str
    ) -> ClauseLineage | None:
        async with self._session_factory() as session:
            return await ClauseLineageRepository(session).get_by_curr_clause(
                curr_clause_id, tenant_id
            )

    async def clause_lineage(
        self, clause_id: int, tenant_id: str
    ) -> ClauseLineageView | None:
        """Trace a clause across every round of the negotiation.

        Walks the persisted ``ClauseLineage`` links backward (to earlier rounds)
        and forward (to later rounds) from ``clause_id`` and assembles, in round
        order, each round's clause text plus the change into it. Because the walk
        follows the stored links — which an override rewrites — the lineage
        follows human alignment corrections (decision #5). Returns ``None`` if
        the clause does not exist.
        """
        async with self._session_factory() as session:
            clauses = ClauseRepository(session)
            lineage_repo = ClauseLineageRepository(session)
            changes = ChangeRepository(session)
            rounds = RoundRepository(session)

            start = await clauses.get(clause_id, tenant_id)
            if start is None:
                return None

            chain: list[Clause] = [start]
            seen: set[int] = {start.id}

            # Backward: follow each clause's prior link to earlier rounds.
            cursor = start
            while True:
                link = await lineage_repo.get_by_curr_clause(cursor.id, tenant_id)
                if link is None or link.prev_clause_id is None:
                    break
                if link.prev_clause_id in seen:
                    break
                prev = await clauses.get(link.prev_clause_id, tenant_id)
                if prev is None:
                    break
                chain.insert(0, prev)
                seen.add(prev.id)
                cursor = prev

            # Forward: follow the link out of each clause into later rounds.
            cursor = start
            while True:
                link = await lineage_repo.get_by_prev_clause(cursor.id, tenant_id)
                if link is None or link.curr_clause_id in seen:
                    break
                nxt = await clauses.get(link.curr_clause_id, tenant_id)
                if nxt is None:
                    break
                chain.append(nxt)
                seen.add(nxt.id)
                cursor = nxt

            entries: list[LineageEntry] = []
            for clause in chain:
                entries.append(
                    LineageEntry(
                        clause=clause,
                        round=await rounds.get(clause.round_id, tenant_id),
                        change=await changes.get_by_curr_clause(clause.id, tenant_id),
                        lineage=await lineage_repo.get_by_curr_clause(
                            clause.id, tenant_id
                        ),
                    )
                )
            entries.sort(key=lambda e: e.round.round_no)
            return ClauseLineageView(
                clause_id=clause_id,
                negotiation_id=entries[0].round.negotiation_id,
                entries=entries,
            )


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
