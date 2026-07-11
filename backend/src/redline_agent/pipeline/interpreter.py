"""Interpreter stage.

Annotates each detected change with a plain-English summary and a materiality
tag. The deterministic differ remains the sole authority on *which* changes
exist (decision #1); this stage only fills interpretation columns and must
never add or drop a change.

Cost control (per the PRD): a cheap deterministic pre-filter tags
whitespace/case/punctuation-only modifications as cosmetic and skips the LLM
for them. The remaining material candidates are interpreted per-change,
concurrently, and deduped by content so identical changes cost a single call.
"""

from __future__ import annotations

import asyncio
import re

from redline_agent.domain import Change, ChangeType, Materiality
from redline_agent.infra.llm.interpreter import (
    InterpretationRequest,
    LLMInterpreter,
)

COSMETIC_SUMMARY = (
    "Cosmetic change: only wording, case, or punctuation differs; no change to "
    "the clause's meaning."
)

_NON_WORD = re.compile(r"[^\w\s]")


def _canonicalize(text: str | None) -> str:
    """Fold case, drop punctuation, and collapse whitespace for comparison."""
    stripped = _NON_WORD.sub(" ", (text or "").lower())
    return " ".join(stripped.split())


def _is_cosmetic(change: Change) -> bool:
    """A modification whose before/after differ only cosmetically.

    Added and removed clauses are always treated as material candidates.
    """
    if change.change_type is not ChangeType.MODIFIED:
        return False
    return _canonicalize(change.raw_before) == _canonicalize(change.raw_after)


async def interpret_changes(
    changes: list[Change],
    interpreter: LLMInterpreter,
    represented_party: str = "",
) -> None:
    """Fill interpretation fields on each material change in place.

    Sets ``summary``/``materiality`` and — for material changes — ``category``,
    ``favored_party`` (relative to ``represented_party``), and ``risk_flag``.
    Never mutates the membership of ``changes`` — only their annotation fields
    (decision #1).
    """
    material: list[Change] = []
    for change in changes:
        if _is_cosmetic(change):
            change.materiality = Materiality.COSMETIC
            change.summary = COSMETIC_SUMMARY
        else:
            material.append(change)

    # Dedupe by content so identical changes are interpreted once (caching).
    by_content: dict[tuple, list[Change]] = {}
    for change in material:
        key = (change.change_type, change.raw_before, change.raw_after)
        by_content.setdefault(key, []).append(change)

    async def _run(key: tuple):
        change_type, raw_before, raw_after = key
        interpretation = await interpreter.interpret(
            InterpretationRequest(
                change_type=change_type,
                raw_before=raw_before,
                raw_after=raw_after,
                represented_party=represented_party,
            )
        )
        return key, interpretation

    results = await asyncio.gather(*(_run(key) for key in by_content))

    for key, interpretation in results:
        for change in by_content[key]:
            change.summary = interpretation.summary
            change.materiality = interpretation.materiality
            change.category = interpretation.category
            change.favored_party = interpretation.favored_party
            change.risk_flag = interpretation.risk_flag
            change.interpretation_model = interpreter.model_name
