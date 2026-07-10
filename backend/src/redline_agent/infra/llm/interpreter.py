"""LLMInterpreter Protocol and a deterministic fake.

The interpreter turns a single detected change into a plain-English
annotation. It is a Protocol (decision #7: the model is swappable and gets
benchmarked before the default is locked); the real Azure OpenAI implementation
lives beside this module. Interpretation only ever *annotates* a change — it
never adds, drops, or edits the set of changes (decision #1).

``FakeInterpreter`` is the offline stand-in used by tests and by local dev when
no LLM provider is configured. It is deterministic and never touches the
network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from redline_agent.domain import ChangeType, Materiality


@dataclass
class InterpretationRequest:
    """The deterministic evidence handed to the interpreter for one change."""

    change_type: ChangeType
    raw_before: str | None
    raw_after: str | None


@dataclass
class Interpretation:
    """The structured annotation produced for one change.

    This slice populates a plain-English ``summary`` and a ``materiality`` tag;
    favored-party, category, and risk arrive in a later slice.
    """

    summary: str
    materiality: Materiality


class LLMInterpreter(Protocol):
    """Explains what a single detected change means. Swappable per decision #7."""

    @property
    def model_name(self) -> str:
        """Identifier of the model/deployment, recorded per interpreted change."""
        ...

    async def interpret(self, request: InterpretationRequest) -> Interpretation:
        """Return a plain-English annotation for one change."""
        ...


def _default_summary(request: InterpretationRequest) -> str:
    if request.change_type is ChangeType.ADDED:
        return "A new clause was added."
    if request.change_type is ChangeType.REMOVED:
        return "An existing clause was removed."
    return "The clause text was modified."


class FakeInterpreter:
    """Deterministic, offline ``LLMInterpreter`` for tests and local dev.

    Returns a canned (or per-change default) summary and a fixed materiality,
    and counts calls so tests can assert per-change and caching behavior.
    """

    def __init__(
        self,
        summary: str | None = None,
        materiality: Materiality = Materiality.SUBSTANTIVE,
        model_name: str = "fake",
    ) -> None:
        self._summary = summary
        self._materiality = materiality
        self._model_name = model_name
        self.calls = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    async def interpret(self, request: InterpretationRequest) -> Interpretation:
        self.calls += 1
        return Interpretation(
            summary=self._summary or _default_summary(request),
            materiality=self._materiality,
        )
