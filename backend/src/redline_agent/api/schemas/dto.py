"""Request/response DTOs for the REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from redline_agent.domain import Change, Negotiation, Round


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

    @classmethod
    def of(cls, c: Change) -> "ChangeOut":
        return cls(
            id=c.id,
            change_type=c.change_type.value,
            curr_clause_id=c.curr_clause_id,
            prev_clause_id=c.prev_clause_id,
            raw_before=c.raw_before,
            raw_after=c.raw_after,
            summary=c.summary,
            materiality=c.materiality.value if c.materiality else None,
            category=c.category,
            favored_party=c.favored_party,
            risk_flag=c.risk_flag,
        )
