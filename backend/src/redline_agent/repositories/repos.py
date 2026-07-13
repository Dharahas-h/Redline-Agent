"""Per-entity repositories.

Each repository wraps an ``AsyncSession`` and maps between ORM rows and pure
domain models. All queries are tenant-scoped. Repositories flush (to obtain
generated ids) but do not commit; the unit of work is owned by the caller.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from redline_agent.domain import (
    AlertType,
    AlignMethod,
    Category,
    Change,
    ChangeType,
    Clause,
    ClauseLineage,
    Export,
    FavoredParty,
    Materiality,
    Negotiation,
    Round,
    RoundStatus,
    StructuralAlert,
)
from redline_agent.repositories.orm import (
    ChangeRow,
    ClauseLineageRow,
    ClauseRow,
    ExportRow,
    NegotiationRow,
    RoundRow,
    StructuralAlertRow,
)


def _to_negotiation(row: NegotiationRow) -> Negotiation:
    return Negotiation(
        id=row.id,
        tenant_id=row.tenant_id,
        title=row.title,
        represented_party=row.represented_party,
        created_at=row.created_at,
    )


def _to_round(row: RoundRow) -> Round:
    return Round(
        id=row.id,
        tenant_id=row.tenant_id,
        negotiation_id=row.negotiation_id,
        round_no=row.round_no,
        submitted_by_party=row.submitted_by_party,
        blob_uri=row.blob_uri,
        canonical_text=row.canonical_text,
        table_signatures=(
            json.loads(row.table_signatures) if row.table_signatures else None
        ),
        status=RoundStatus(row.status),
        created_at=row.created_at,
    )


def _to_clause(row: ClauseRow) -> Clause:
    return Clause(
        id=row.id,
        tenant_id=row.tenant_id,
        round_id=row.round_id,
        ordinal=row.ordinal,
        number_label=row.number_label,
        heading=row.heading,
        text=row.text,
        embedding=json.loads(row.embedding) if row.embedding else None,
    )


def _to_change(row: ChangeRow) -> Change:
    return Change(
        id=row.id,
        tenant_id=row.tenant_id,
        negotiation_id=row.negotiation_id,
        from_round_id=row.from_round_id,
        to_round_id=row.to_round_id,
        curr_clause_id=row.curr_clause_id,
        prev_clause_id=row.prev_clause_id,
        change_type=ChangeType(row.change_type),
        raw_before=row.raw_before,
        raw_after=row.raw_after,
        summary=row.summary,
        materiality=Materiality(row.materiality) if row.materiality else None,
        category=Category(row.category) if row.category else None,
        favored_party=(
            FavoredParty(row.favored_party) if row.favored_party else None
        ),
        risk_flag=row.risk_flag,
        interpretation_model=row.interpretation_model,
    )


class NegotiationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, negotiation: Negotiation) -> Negotiation:
        row = NegotiationRow(
            tenant_id=negotiation.tenant_id,
            title=negotiation.title,
            represented_party=negotiation.represented_party,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_negotiation(row)

    async def get(self, negotiation_id: int, tenant_id: str) -> Negotiation | None:
        row = await self._session.get(NegotiationRow, negotiation_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_negotiation(row)

    async def list(self, tenant_id: str) -> list[Negotiation]:
        stmt = (
            select(NegotiationRow)
            .where(NegotiationRow.tenant_id == tenant_id)
            .order_by(NegotiationRow.created_at.desc())
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_negotiation(r) for r in rows]

    async def delete(self, negotiation_id: int, tenant_id: str) -> None:
        row = await self._session.get(NegotiationRow, negotiation_id)
        if row is not None and row.tenant_id == tenant_id:
            await self._session.delete(row)
            await self._session.flush()


class RoundRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, round_: Round) -> Round:
        row = RoundRow(
            tenant_id=round_.tenant_id,
            negotiation_id=round_.negotiation_id,
            round_no=round_.round_no,
            submitted_by_party=round_.submitted_by_party,
            blob_uri=round_.blob_uri,
            canonical_text=round_.canonical_text,
            table_signatures=(
                json.dumps(round_.table_signatures)
                if round_.table_signatures is not None
                else None
            ),
            status=round_.status.value,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_round(row)

    async def get(self, round_id: int, tenant_id: str) -> Round | None:
        row = await self._session.get(RoundRow, round_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_round(row)

    async def list_for_negotiation(
        self, negotiation_id: int, tenant_id: str
    ) -> list[Round]:
        stmt = (
            select(RoundRow)
            .where(
                RoundRow.negotiation_id == negotiation_id,
                RoundRow.tenant_id == tenant_id,
            )
            .order_by(RoundRow.round_no)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_round(r) for r in rows]

    async def next_round_no(self, negotiation_id: int, tenant_id: str) -> int:
        rounds = await self.list_for_negotiation(negotiation_id, tenant_id)
        return (max((r.round_no for r in rounds), default=0)) + 1

    async def prior_round(
        self, negotiation_id: int, round_no: int, tenant_id: str
    ) -> Round | None:
        rounds = await self.list_for_negotiation(negotiation_id, tenant_id)
        prior = [r for r in rounds if r.round_no < round_no]
        return prior[-1] if prior else None

    async def set_status(self, round_id: int, status: RoundStatus) -> None:
        row = await self._session.get(RoundRow, round_id)
        if row is not None:
            row.status = status.value
            await self._session.flush()

    async def delete(self, round_id: int, tenant_id: str) -> None:
        row = await self._session.get(RoundRow, round_id)
        if row is not None and row.tenant_id == tenant_id:
            await self._session.delete(row)
            await self._session.flush()


class ClauseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, clauses: list[Clause]) -> list[Clause]:
        rows = [
            ClauseRow(
                tenant_id=c.tenant_id,
                round_id=c.round_id,
                ordinal=c.ordinal,
                number_label=c.number_label,
                heading=c.heading,
                text=c.text,
                embedding=json.dumps(c.embedding) if c.embedding else None,
            )
            for c in clauses
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return [_to_clause(r) for r in rows]

    async def list_for_round(self, round_id: int, tenant_id: str) -> list[Clause]:
        stmt = (
            select(ClauseRow)
            .where(ClauseRow.round_id == round_id, ClauseRow.tenant_id == tenant_id)
            .order_by(ClauseRow.ordinal)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_clause(r) for r in rows]

    async def get(self, clause_id: int, tenant_id: str) -> Clause | None:
        row = await self._session.get(ClauseRow, clause_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_clause(row)

    async def delete_for_round(self, round_id: int, tenant_id: str) -> None:
        stmt = select(ClauseRow).where(
            ClauseRow.round_id == round_id, ClauseRow.tenant_id == tenant_id
        )
        for row in (await self._session.scalars(stmt)).all():
            await self._session.delete(row)
        await self._session.flush()


def _to_lineage(row: ClauseLineageRow) -> ClauseLineage:
    return ClauseLineage(
        id=row.id,
        tenant_id=row.tenant_id,
        negotiation_id=row.negotiation_id,
        prev_clause_id=row.prev_clause_id,
        curr_clause_id=row.curr_clause_id,
        similarity=row.similarity,
        confidence=row.confidence,
        align_method=AlignMethod(row.align_method),
        overridden=row.overridden,
    )


class ClauseLineageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, lineage: ClauseLineage) -> ClauseLineage:
        row = ClauseLineageRow(
            tenant_id=lineage.tenant_id,
            negotiation_id=lineage.negotiation_id,
            prev_clause_id=lineage.prev_clause_id,
            curr_clause_id=lineage.curr_clause_id,
            similarity=lineage.similarity,
            confidence=lineage.confidence,
            align_method=lineage.align_method.value,
            overridden=lineage.overridden,
        )
        self._session.add(row)
        await self._session.flush()
        lineage.id = row.id
        return lineage

    async def get_by_curr_clause(
        self, curr_clause_id: int, tenant_id: str
    ) -> ClauseLineage | None:
        stmt = select(ClauseLineageRow).where(
            ClauseLineageRow.curr_clause_id == curr_clause_id,
            ClauseLineageRow.tenant_id == tenant_id,
        )
        row = (await self._session.scalars(stmt)).first()
        return _to_lineage(row) if row is not None else None

    async def get_by_prev_clause(
        self, prev_clause_id: int, tenant_id: str
    ) -> ClauseLineage | None:
        """The link whose prior clause is ``prev_clause_id`` (forward step).

        Follows the chain into the next round. A split points several current
        clauses at one prior; we take the first, so lineage follows the primary
        forward chain.
        """
        stmt = select(ClauseLineageRow).where(
            ClauseLineageRow.prev_clause_id == prev_clause_id,
            ClauseLineageRow.tenant_id == tenant_id,
        )
        row = (await self._session.scalars(stmt)).first()
        return _to_lineage(row) if row is not None else None

    async def list_for_round(
        self, round_id: int, tenant_id: str
    ) -> list[ClauseLineage]:
        """Lineage links whose current clause belongs to ``round_id``."""
        stmt = (
            select(ClauseLineageRow)
            .join(ClauseRow, ClauseLineageRow.curr_clause_id == ClauseRow.id)
            .where(
                ClauseRow.round_id == round_id,
                ClauseLineageRow.tenant_id == tenant_id,
            )
            .order_by(ClauseRow.ordinal)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_lineage(r) for r in rows]

    async def delete_for_round(self, round_id: int, tenant_id: str) -> None:
        """Drop lineage links whose current clause belongs to ``round_id``.

        The latest round is never a ``prev`` clause (nothing was diffed against
        it yet), so its links are exactly those keyed by its current clauses.
        """
        stmt = (
            select(ClauseLineageRow)
            .join(ClauseRow, ClauseLineageRow.curr_clause_id == ClauseRow.id)
            .where(
                ClauseRow.round_id == round_id,
                ClauseLineageRow.tenant_id == tenant_id,
            )
        )
        for row in (await self._session.scalars(stmt)).all():
            await self._session.delete(row)
        await self._session.flush()

    async def update(self, lineage: ClauseLineage) -> ClauseLineage:
        row = await self._session.get(ClauseLineageRow, lineage.id)
        if row is not None and row.tenant_id == lineage.tenant_id:
            row.prev_clause_id = lineage.prev_clause_id
            row.similarity = lineage.similarity
            row.confidence = lineage.confidence
            row.align_method = lineage.align_method.value
            row.overridden = lineage.overridden
            await self._session.flush()
        return lineage


def _to_export(row: ExportRow) -> Export:
    return Export(
        id=row.id,
        tenant_id=row.tenant_id,
        negotiation_id=row.negotiation_id,
        from_round_id=row.from_round_id,
        to_round_id=row.to_round_id,
        filename=row.filename,
        blob_uri=row.blob_uri,
        created_at=row.created_at,
    )


class ExportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, export: Export) -> Export:
        row = ExportRow(
            tenant_id=export.tenant_id,
            negotiation_id=export.negotiation_id,
            from_round_id=export.from_round_id,
            to_round_id=export.to_round_id,
            filename=export.filename,
            blob_uri=export.blob_uri,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_export(row)

    async def get(self, export_id: int, tenant_id: str) -> Export | None:
        row = await self._session.get(ExportRow, export_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_export(row)

    async def delete_for_round(self, round_id: int, tenant_id: str) -> list[str]:
        """Delete exports touching ``round_id`` and return their blob URIs.

        Matches either endpoint so a round's exports are removed regardless of
        whether it was the ``from`` or ``to`` side of the redline.
        """
        stmt = select(ExportRow).where(
            ExportRow.tenant_id == tenant_id,
            (ExportRow.to_round_id == round_id)
            | (ExportRow.from_round_id == round_id),
        )
        blob_uris: list[str] = []
        for row in (await self._session.scalars(stmt)).all():
            if row.blob_uri:
                blob_uris.append(row.blob_uri)
            await self._session.delete(row)
        await self._session.flush()
        return blob_uris


class ChangeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(self, changes: list[Change]) -> list[Change]:
        rows = [
            ChangeRow(
                tenant_id=c.tenant_id,
                negotiation_id=c.negotiation_id,
                from_round_id=c.from_round_id,
                to_round_id=c.to_round_id,
                curr_clause_id=c.curr_clause_id,
                prev_clause_id=c.prev_clause_id,
                change_type=c.change_type.value,
                raw_before=c.raw_before,
                raw_after=c.raw_after,
                summary=c.summary,
                materiality=c.materiality.value if c.materiality else None,
                category=c.category.value if c.category else None,
                favored_party=c.favored_party.value if c.favored_party else None,
                risk_flag=c.risk_flag,
                interpretation_model=c.interpretation_model,
            )
            for c in changes
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return [_to_change(r) for r in rows]

    async def list_for_round(self, to_round_id: int, tenant_id: str) -> list[Change]:
        stmt = (
            select(ChangeRow)
            .where(
                ChangeRow.to_round_id == to_round_id,
                ChangeRow.tenant_id == tenant_id,
            )
            .order_by(ChangeRow.id)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_change(r) for r in rows]

    async def get(self, change_id: int, tenant_id: str) -> Change | None:
        row = await self._session.get(ChangeRow, change_id)
        if row is None or row.tenant_id != tenant_id:
            return None
        return _to_change(row)

    async def get_by_curr_clause(
        self, curr_clause_id: int, tenant_id: str
    ) -> Change | None:
        """The change into ``curr_clause_id`` — how that clause changed from the
        prior round. ``None`` for a clause that carries no change (e.g. a
        first-round clause)."""
        stmt = select(ChangeRow).where(
            ChangeRow.curr_clause_id == curr_clause_id,
            ChangeRow.tenant_id == tenant_id,
        )
        row = (await self._session.scalars(stmt)).first()
        return _to_change(row) if row is not None else None

    async def delete_for_round(self, to_round_id: int, tenant_id: str) -> None:
        """Drop this round's changes so they can be regenerated from scratch."""
        stmt = select(ChangeRow).where(
            ChangeRow.to_round_id == to_round_id,
            ChangeRow.tenant_id == tenant_id,
        )
        for row in (await self._session.scalars(stmt)).all():
            await self._session.delete(row)
        await self._session.flush()


def _to_alert(row: StructuralAlertRow) -> StructuralAlert:
    return StructuralAlert(
        id=row.id,
        tenant_id=row.tenant_id,
        negotiation_id=row.negotiation_id,
        from_round_id=row.from_round_id,
        to_round_id=row.to_round_id,
        alert_type=AlertType(row.alert_type),
        subject=row.subject,
        detail=row.detail,
        affected_clause_count=row.affected_clause_count,
    )


class StructuralAlertRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_many(
        self, alerts: list[StructuralAlert]
    ) -> list[StructuralAlert]:
        rows = [
            StructuralAlertRow(
                tenant_id=a.tenant_id,
                negotiation_id=a.negotiation_id,
                from_round_id=a.from_round_id,
                to_round_id=a.to_round_id,
                alert_type=a.alert_type.value,
                subject=a.subject,
                detail=a.detail,
                affected_clause_count=a.affected_clause_count,
            )
            for a in alerts
        ]
        self._session.add_all(rows)
        await self._session.flush()
        return [_to_alert(r) for r in rows]

    async def list_for_round(
        self, to_round_id: int, tenant_id: str
    ) -> list[StructuralAlert]:
        stmt = (
            select(StructuralAlertRow)
            .where(
                StructuralAlertRow.to_round_id == to_round_id,
                StructuralAlertRow.tenant_id == tenant_id,
            )
            .order_by(StructuralAlertRow.id)
        )
        rows = (await self._session.scalars(stmt)).all()
        return [_to_alert(r) for r in rows]

    async def delete_for_round(self, to_round_id: int, tenant_id: str) -> None:
        """Drop this round's alerts so they can be regenerated (override re-run)."""
        stmt = select(StructuralAlertRow).where(
            StructuralAlertRow.to_round_id == to_round_id,
            StructuralAlertRow.tenant_id == tenant_id,
        )
        for row in (await self._session.scalars(stmt)).all():
            await self._session.delete(row)
        await self._session.flush()
