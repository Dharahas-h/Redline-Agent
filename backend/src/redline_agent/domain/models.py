"""Pure domain models.

These are plain dataclasses used by the pipeline and services. Persistence is
handled separately in the repositories layer; these carry no ORM or I/O
dependencies so the pipeline stays testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from redline_agent.domain.enums import (
    AlignMethod,
    ChangeType,
    Materiality,
    RoundStatus,
)


@dataclass
class Negotiation:
    """Top-level container for one contract negotiated over time."""

    title: str
    represented_party: str
    tenant_id: str
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class Round:
    """One submitted .docx at a point in time."""

    negotiation_id: int
    round_no: int
    submitted_by_party: str
    tenant_id: str
    blob_uri: str | None = None
    canonical_text: str | None = None
    status: RoundStatus = RoundStatus.PENDING
    id: int | None = None
    created_at: datetime | None = None


@dataclass
class Clause:
    """A logical unit of a round produced by segmentation."""

    round_id: int
    ordinal: int
    text: str
    tenant_id: str
    number_label: str | None = None
    heading: str | None = None
    embedding: list[float] | None = None
    id: int | None = None


@dataclass
class ClauseLineage:
    """A link pairing a clause in one round to its counterpart in the prior."""

    negotiation_id: int
    curr_clause_id: int
    tenant_id: str
    prev_clause_id: int | None = None
    similarity: float | None = None
    confidence: float | None = None
    align_method: AlignMethod = AlignMethod.POSITIONAL
    overridden: bool = False
    id: int | None = None


@dataclass
class Change:
    """A detected delta between a pair of aligned clauses across two rounds.

    The deterministic differ is the sole authority on the existence of a
    change. Interpretation columns (summary, materiality, ...) are nullable
    until the Interpreter stage annotates them.
    """

    negotiation_id: int
    from_round_id: int | None
    to_round_id: int
    change_type: ChangeType
    tenant_id: str
    curr_clause_id: int | None = None
    prev_clause_id: int | None = None
    raw_before: str | None = None
    raw_after: str | None = None
    # Interpretation (nullable until interpreted).
    summary: str | None = None
    materiality: Materiality | None = None
    category: str | None = None
    favored_party: str | None = None
    risk_flag: str | None = None
    interpretation_model: str | None = None
    id: int | None = None
