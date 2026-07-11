"""Request/response DTOs for the REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from typing import TYPE_CHECKING

from redline_agent.domain import (
    Change,
    ClauseLineage,
    Export,
    Negotiation,
    Round,
    StructuralAlert,
)
from redline_agent.pipeline.aligner import is_low_confidence

if TYPE_CHECKING:
    from redline_agent.services.change_query import ClauseLineageView, LineageEntry


class NegotiationCreate(BaseModel):
    title: str = Field(min_length=1)
    represented_party: str = Field(min_length=1)


class NegotiationOut(BaseModel):
    id: int
    title: str
    represented_party: str
    created_at: datetime | None = None

    @classmethod
    def of(cls, n: Negotiation) -> "NegotiationOut":
        return cls(
            id=n.id,
            title=n.title,
            represented_party=n.represented_party,
            created_at=n.created_at,
        )


class RoundOut(BaseModel):
    id: int
    negotiation_id: int
    round_no: int
    submitted_by_party: str
    status: str
    created_at: datetime | None = None

    @classmethod
    def of(cls, r: Round) -> "RoundOut":
        return cls(
            id=r.id,
            negotiation_id=r.negotiation_id,
            round_no=r.round_no,
            submitted_by_party=r.submitted_by_party,
            status=r.status.value,
            created_at=r.created_at,
        )


class NegotiationDetailOut(NegotiationOut):
    rounds: list[RoundOut] = []


class ExportOut(BaseModel):
    id: int
    negotiation_id: int
    from_round_id: int
    to_round_id: int
    filename: str
    created_at: datetime | None = None

    @classmethod
    def of(cls, e: Export) -> "ExportOut":
        return cls(
            id=e.id,
            negotiation_id=e.negotiation_id,
            from_round_id=e.from_round_id,
            to_round_id=e.to_round_id,
            filename=e.filename,
            created_at=e.created_at,
        )


class ChangeOut(BaseModel):
    id: int
    change_type: str
    curr_clause_id: int | None = None
    prev_clause_id: int | None = None
    raw_before: str | None = None
    raw_after: str | None = None
    summary: str | None = None
    materiality: str | None = None
    category: str | None = None
    favored_party: str | None = None
    risk_flag: str | None = None
    # Alignment provenance for this clause (from clause lineage). Lets the feed
    # flag uncertain or human-corrected matches (decision #5).
    alignment_confidence: float | None = None
    alignment_method: str | None = None
    alignment_similarity: float | None = None
    low_confidence: bool = False
    overridden: bool = False

    @classmethod
    def of(cls, c: Change, lineage: "ClauseLineage | None" = None) -> "ChangeOut":
        return cls(
            id=c.id,
            change_type=c.change_type.value,
            curr_clause_id=c.curr_clause_id,
            prev_clause_id=c.prev_clause_id,
            raw_before=c.raw_before,
            raw_after=c.raw_after,
            summary=c.summary,
            materiality=c.materiality.value if c.materiality else None,
            category=c.category.value if c.category else None,
            favored_party=c.favored_party.value if c.favored_party else None,
            risk_flag=c.risk_flag,
            alignment_confidence=lineage.confidence if lineage else None,
            alignment_method=lineage.align_method.value if lineage else None,
            alignment_similarity=lineage.similarity if lineage else None,
            low_confidence=(
                is_low_confidence(lineage.confidence) if lineage else False
            ),
            overridden=lineage.overridden if lineage else False,
        )


class StructuralAlertOut(BaseModel):
    """A structural alert surfaced alongside the feed (definition/table change).

    Not a change: rendered as a prominent banner, separate from the change
    cards (decision #1, #6).
    """

    id: int
    alert_type: str
    subject: str | None = None
    detail: str
    affected_clause_count: int | None = None

    @classmethod
    def of(cls, a: StructuralAlert) -> "StructuralAlertOut":
        return cls(
            id=a.id,
            alert_type=a.alert_type.value,
            subject=a.subject,
            detail=a.detail,
            affected_clause_count=a.affected_clause_count,
        )


class LineageEntryOut(BaseModel):
    """One round's view of a clause in its cross-round lineage."""

    round_id: int
    round_no: int
    submitted_by_party: str
    clause_id: int
    number_label: str | None = None
    heading: str | None = None
    text: str
    # The change into this round's clause (how it changed from the prior round);
    # null for the round where the clause first appears with no prior.
    change: ChangeOut | None = None

    @classmethod
    def of(cls, entry: "LineageEntry") -> "LineageEntryOut":
        return cls(
            round_id=entry.round.id,
            round_no=entry.round.round_no,
            submitted_by_party=entry.round.submitted_by_party,
            clause_id=entry.clause.id,
            number_label=entry.clause.number_label,
            heading=entry.clause.heading,
            text=entry.clause.text,
            change=(
                ChangeOut.of(entry.change, entry.lineage)
                if entry.change is not None
                else None
            ),
        )


class ClauseLineageOut(BaseModel):
    """A clause's evolution across every round of the negotiation, in order."""

    clause_id: int
    negotiation_id: int
    entries: list[LineageEntryOut] = []

    @classmethod
    def of(cls, view: "ClauseLineageView") -> "ClauseLineageOut":
        return cls(
            clause_id=view.clause_id,
            negotiation_id=view.negotiation_id,
            entries=[LineageEntryOut.of(e) for e in view.entries],
        )
