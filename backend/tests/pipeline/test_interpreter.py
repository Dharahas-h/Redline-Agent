"""Interpreter stage: fills summary + materiality on changes via LLMInterpreter.

The stage annotates changes only — it must never add or drop a change
(decision #1). Whitespace/case/punctuation-only modifications are classified
cosmetic deterministically and skip the LLM; material candidates are
interpreted per-change, concurrently, and deduped by content (caching).
"""

import pytest

from redline_agent.domain import (
    Category,
    Change,
    ChangeType,
    FavoredParty,
    Materiality,
)
from redline_agent.infra.llm.interpreter import (
    FakeInterpreter,
    Interpretation,
)
from redline_agent.pipeline.interpreter import interpret_changes

TENANT = "t"


def _change(change_type, before, after, **kw):
    return Change(
        negotiation_id=1,
        from_round_id=1,
        to_round_id=2,
        change_type=change_type,
        tenant_id=TENANT,
        raw_before=before,
        raw_after=after,
        **kw,
    )


async def test_material_change_gets_summary_and_materiality():
    interp = FakeInterpreter(
        summary="Payment window extended from 30 to 45 days.",
        materiality=Materiality.SUBSTANTIVE,
        model_name="fake-model",
    )
    change = _change(ChangeType.MODIFIED, "pay within 30 days", "pay within 45 days")

    await interpret_changes([change], interp)

    assert change.summary == "Payment window extended from 30 to 45 days."
    assert change.materiality is Materiality.SUBSTANTIVE
    assert change.interpretation_model == "fake-model"
    assert interp.calls == 1


async def test_cosmetic_change_skips_the_llm():
    interp = FakeInterpreter(materiality=Materiality.SUBSTANTIVE)
    # Differs only by trailing punctuation and case -> cosmetic.
    change = _change(ChangeType.MODIFIED, "This Agreement lasts one year.", "this agreement lasts one year")

    await interpret_changes([change], interp)

    assert change.materiality is Materiality.COSMETIC
    assert change.summary  # a human-readable note is set
    assert interp.calls == 0  # the LLM was not invoked
    assert change.interpretation_model is None


async def test_added_and_removed_are_material_candidates():
    interp = FakeInterpreter(materiality=Materiality.SUBSTANTIVE)
    added = _change(ChangeType.ADDED, None, "New confidentiality clause.")
    removed = _change(ChangeType.REMOVED, "Old indemnity clause.", None)

    await interpret_changes([added, removed], interp)

    assert added.materiality is Materiality.SUBSTANTIVE
    assert removed.materiality is Materiality.SUBSTANTIVE
    assert interp.calls == 2


async def test_identical_changes_are_interpreted_once_cached():
    interp = FakeInterpreter(materiality=Materiality.SUBSTANTIVE)
    a = _change(ChangeType.MODIFIED, "pay within 30 days", "pay within 45 days")
    b = _change(ChangeType.MODIFIED, "pay within 30 days", "pay within 45 days")
    c = _change(ChangeType.MODIFIED, "term is 1 year", "term is 2 years")

    await interpret_changes([a, b, c], interp)

    # Two unique contents -> two calls, though three changes were annotated.
    assert interp.calls == 2
    assert a.summary == b.summary
    assert all(x.materiality is Materiality.SUBSTANTIVE for x in (a, b, c))


async def test_material_change_gets_favored_party_category_and_risk():
    interp = FakeInterpreter(
        summary="Cap on liability lowered.",
        materiality=Materiality.SUBSTANTIVE,
        category=Category.LIABILITY,
        favored_party=FavoredParty.COUNTERPARTY,
        risk_flag="For attorney review: the liability cap was reduced.",
    )
    change = _change(ChangeType.MODIFIED, "cap is $1M", "cap is $100k")

    await interpret_changes([change], interp, represented_party="Buyer")

    assert change.category is Category.LIABILITY
    assert change.favored_party is FavoredParty.COUNTERPARTY
    assert change.risk_flag == "For attorney review: the liability cap was reduced."


async def test_represented_party_is_passed_to_the_interpreter():
    # Favored-party is computed relative to the represented party, so the stage
    # must thread it into every request.
    interp = FakeInterpreter(favored_party=FavoredParty.REPRESENTED)
    change = _change(ChangeType.MODIFIED, "pay within 30 days", "pay within 45 days")

    await interpret_changes([change], interp, represented_party="Acme Corp")

    assert interp.requests[0].represented_party == "Acme Corp"


async def test_cosmetic_change_has_no_favored_party_category_or_risk():
    interp = FakeInterpreter(
        category=Category.PAYMENT,
        favored_party=FavoredParty.COUNTERPARTY,
        risk_flag="should not be applied",
    )
    change = _change(ChangeType.MODIFIED, "This Agreement lasts one year.", "this agreement lasts one year")

    await interpret_changes([change], interp, represented_party="Buyer")

    assert change.materiality is Materiality.COSMETIC
    assert change.category is None
    assert change.favored_party is None
    assert change.risk_flag is None
    assert interp.calls == 0


async def test_stage_never_adds_or_drops_changes():
    interp = FakeInterpreter(summary="garbage", materiality=Materiality.SUBSTANTIVE)
    changes = [
        _change(ChangeType.MODIFIED, "pay within 30 days", "pay within 45 days"),
        _change(ChangeType.ADDED, None, "New clause."),
    ]

    await interpret_changes(changes, interp)

    assert len(changes) == 2  # same objects, none added/removed
