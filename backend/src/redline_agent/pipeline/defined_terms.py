"""Defined-terms stage.

Detects when a defined term's *definition* changed between rounds and counts how
many clauses in the new round reference that term — the "ripple" a definitional
edit implies (decision #6). This is a structural alert, not a ``Change``: the
deterministic differ remains the sole authority on the set of changes
(decision #1), so nothing here adds to or removes from it.

Operates on clause texts (canonical, already segmented), keeping the stage
text-based and testable in isolation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# A defined-term definition: a quoted term (straight or curly quotes) followed
# by "means" / "shall mean", optionally with a trailing colon.
_DEFINITION = re.compile(
    r"""["“'‘]([^"”'’]+)["”'’]\s+(?:shall\s+mean|means?)\b[:\s]*""",
    re.IGNORECASE,
)


def _normalize(text: str) -> str:
    """Collapse whitespace so definition comparisons ignore formatting noise."""
    return " ".join(text.split())


def extract_definitions(clause_texts: list[str]) -> dict[str, tuple[str, str]]:
    """Map each defined term (keyed lowercase) to ``(display_term, definition)``.

    A clause may define several terms; each definition runs from its ``means``
    keyword to the start of the next definition (or the end of the clause). The
    first definition of a term wins.
    """
    definitions: dict[str, tuple[str, str]] = {}
    for text in clause_texts:
        matches = list(_DEFINITION.finditer(text))
        for i, match in enumerate(matches):
            term = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            key = term.lower()
            if key not in definitions:
                definitions[key] = (term, _normalize(text[start:end]))
    return definitions


def _defines(term: str, text: str) -> bool:
    """Whether ``text`` is a clause that defines ``term``."""
    lowered = term.lower()
    return any(m.group(1).strip().lower() == lowered for m in _DEFINITION.finditer(text))


def count_references(term: str, clause_texts: list[str]) -> int:
    """Count clauses that mention ``term``, excluding the clause that defines it."""
    mention = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
    count = 0
    for text in clause_texts:
        if not mention.search(text):
            continue
        if _defines(term, text):
            continue
        count += 1
    return count


@dataclass
class DefinitionChange:
    """A defined term whose definition changed, with its reference ripple count."""

    term: str
    definition_before: str
    definition_after: str
    affected_clause_count: int


def detect_definition_changes(
    prev_texts: list[str], curr_texts: list[str]
) -> list[DefinitionChange]:
    """Terms defined in both rounds whose definition text differs.

    A term that only appears in the new round is a *new* definition, not a
    redefinition, so it is not reported here. Results are ordered by term for
    determinism.
    """
    prev = extract_definitions(prev_texts)
    curr = extract_definitions(curr_texts)
    changes: list[DefinitionChange] = []
    for key, (term, curr_def) in curr.items():
        if key not in prev:
            continue
        prev_def = prev[key][1]
        if prev_def == curr_def:
            continue
        changes.append(
            DefinitionChange(
                term=term,
                definition_before=prev_def,
                definition_after=curr_def,
                affected_clause_count=count_references(term, curr_texts),
            )
        )
    return sorted(changes, key=lambda c: c.term.lower())
