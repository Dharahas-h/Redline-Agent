"""FakeAdjudicator: deterministic, records requests, clamps out-of-range picks."""

from redline_agent.infra.llm.adjudicator import (
    AdjudicationRequest,
    FakeAdjudicator,
)


async def test_returns_configured_choice_and_confidence():
    adj = FakeAdjudicator(choice=1, confidence=0.6)
    result = await adj.adjudicate(
        AdjudicationRequest(curr_text="c", candidates=["a", "b", "c"])
    )
    assert result.choice == 1
    assert result.confidence == 0.6
    assert adj.calls == 1
    assert adj.requests[0].curr_text == "c"


async def test_out_of_range_choice_becomes_no_match():
    adj = FakeAdjudicator(choice=3)
    result = await adj.adjudicate(
        AdjudicationRequest(curr_text="c", candidates=["a"])
    )
    assert result.choice is None


async def test_none_choice_is_a_new_clause():
    adj = FakeAdjudicator(choice=None)
    result = await adj.adjudicate(
        AdjudicationRequest(curr_text="c", candidates=["a", "b"])
    )
    assert result.choice is None
