"""SQLAlchemy ORM mapping.

Tenant-ready from the first migration: ``tenant_id`` is present on every
top-level table (decision #8). The schema mirrors the data model in
ARCHITECTURE.md. It is engine-agnostic; SQLite backs dev/test and Postgres is a
configuration swap. ``clauses.embedding`` is stored as JSON text here (pgvector
is the Postgres-side representation).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class NegotiationRow(Base):
    __tablename__ = "negotiations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    represented_party: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    rounds: Mapped[list["RoundRow"]] = relationship(
        back_populates="negotiation", order_by="RoundRow.round_no"
    )


class RoundRow(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    negotiation_id: Mapped[int] = mapped_column(
        ForeignKey("negotiations.id"), index=True
    )
    round_no: Mapped[int] = mapped_column(Integer)
    submitted_by_party: Mapped[str] = mapped_column(String)
    blob_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    canonical_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    negotiation: Mapped[NegotiationRow] = relationship(back_populates="rounds")
    clauses: Mapped[list["ClauseRow"]] = relationship(
        back_populates="round", order_by="ClauseRow.ordinal"
    )


class ClauseRow(Base):
    __tablename__ = "clauses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    number_label: Mapped[str | None] = mapped_column(String, nullable=True)
    heading: Mapped[str | None] = mapped_column(String, nullable=True)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)

    round: Mapped[RoundRow] = relationship(back_populates="clauses")


class ClauseLineageRow(Base):
    __tablename__ = "clause_lineage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    negotiation_id: Mapped[int] = mapped_column(
        ForeignKey("negotiations.id"), index=True
    )
    prev_clause_id: Mapped[int | None] = mapped_column(
        ForeignKey("clauses.id"), nullable=True
    )
    curr_clause_id: Mapped[int] = mapped_column(
        ForeignKey("clauses.id"), index=True
    )
    similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    align_method: Mapped[str] = mapped_column(String, default="positional")
    overridden: Mapped[bool] = mapped_column(Boolean, default=False)


class ExportRow(Base):
    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    negotiation_id: Mapped[int] = mapped_column(
        ForeignKey("negotiations.id"), index=True
    )
    from_round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    to_round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    filename: Mapped[str] = mapped_column(String)
    blob_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ChangeRow(Base):
    __tablename__ = "changes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    negotiation_id: Mapped[int] = mapped_column(
        ForeignKey("negotiations.id"), index=True
    )
    from_round_id: Mapped[int | None] = mapped_column(
        ForeignKey("rounds.id"), nullable=True
    )
    to_round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"), index=True)
    curr_clause_id: Mapped[int | None] = mapped_column(
        ForeignKey("clauses.id"), nullable=True
    )
    prev_clause_id: Mapped[int | None] = mapped_column(
        ForeignKey("clauses.id"), nullable=True
    )
    change_type: Mapped[str] = mapped_column(String)
    raw_before: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_after: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Interpretation columns, nullable until the Interpreter stage runs.
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    materiality: Mapped[str | None] = mapped_column(String, nullable=True)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    favored_party: Mapped[str | None] = mapped_column(String, nullable=True)
    risk_flag: Mapped[str | None] = mapped_column(Text, nullable=True)
    interpretation_model: Mapped[str | None] = mapped_column(
        String, nullable=True
    )
