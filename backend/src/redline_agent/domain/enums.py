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


class AlignMethod(str, Enum):
    """How a clause lineage link was established."""

    POSITIONAL = "positional"
    EMBEDDING = "embedding"
    HEADING = "heading"
    LLM = "llm"
    OVERRIDE = "override"
