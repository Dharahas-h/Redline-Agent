"""Pure domain models.

These are plain dataclasses used by the pipeline and services. Persistence is
handled separately in the repositories layer; these carry no ORM or I/O
dependencies so the pipeline stays testable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from redline_agent.domain.enums import (
    AlertType,
    AlignMethod,
    Category,
    ChangeType,
    FavoredParty,
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
    # Flattened per-table cell text, one signature per table, for detect-and-flag
    # table-change alerts (tables are dropped from canonical text; decision #6).
    table_signatures: list[str] | None = None
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
class Export:
    """A generated tracked-changes ``.docx`` (latest round vs prior).

    The bytes live in the blob store; this row records what was exported and
    points at them by ``blob_uri``.
    """

    negotiation_id: int
    from_round_id: int
    to_round_id: int
    tenant_id: str
    filename: str
    blob_uri: str | None = None
    id: int | None = None
    created_at: datetime | None = None


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
    category: Category | None = None
    favored_party: FavoredParty | None = None
    risk_flag: str | None = None
    interpretation_model: str | None = None
    id: int | None = None


@dataclass
class StructuralAlert:
    """A high-value structural event flagged alongside a round's change feed.

    Not a ``Change``: the deterministic differ owns the change set (decision #1).
    ``subject`` is the defined term (for a definition change) or ``None`` for a
    table; ``affected_clause_count`` is the reference ripple count for a
    definition change and ``None`` for a table (decision #6).
    """

    negotiation_id: int
    from_round_id: int
    to_round_id: int
    alert_type: AlertType
    detail: str
    tenant_id: str
    subject: str | None = None
    affected_clause_count: int | None = None
    id: int | None = None
