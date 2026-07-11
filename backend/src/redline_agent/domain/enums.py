"""Domain enumerations. Glossary terms are used verbatim."""

from enum import Enum


class RoundStatus(str, Enum):
    """Lifecycle of a round's pipeline processing, pollable by the client."""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ChangeType(str, Enum):
    """The kind of delta the deterministic differ detected for a clause."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"


class Materiality(str, Enum):
    """Whether a change is substantive or cosmetic. Set by interpretation."""

    SUBSTANTIVE = "substantive"
    COSMETIC = "cosmetic"


class Category(str, Enum):
    """The subject tag of a change. Set by interpretation.

    A controlled vocabulary keeps the feed filterable; ``OTHER`` is the catch-all
    for changes that do not fall into a named subject.
    """

    PAYMENT = "payment"
    LIABILITY = "liability"
    IP = "ip"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"


class FavoredParty(str, Enum):
    """Which side a change benefits, *relative to* the represented party.

    Stored relative (not as a party name) so the feed can render a "favors me /
    favors them" badge without needing the negotiation's party names.
    """

    REPRESENTED = "represented"
    COUNTERPARTY = "counterparty"
    NEUTRAL = "neutral"


class AlignMethod(str, Enum):
    """How a clause lineage link was established."""

    POSITIONAL = "positional"
    EMBEDDING = "embedding"
    HEADING = "heading"
    LLM = "llm"
    OVERRIDE = "override"
