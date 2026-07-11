"""Azure OpenAI implementation of the LLMInterpreter Protocol.

This is the default interpreter in deployment (decision #7). It is never
exercised by tests (no test hits the network — the ``FakeInterpreter`` stands
in); the ``openai`` client is imported lazily so this module imports cleanly
even when the package or credentials are absent.

Enterprise no-training / data-residency terms are a gating requirement for the
provider handling legal documents; confirming them is the human-in-the-loop
step in the "lock the interpretation model" issue.
"""

from __future__ import annotations

import json

from redline_agent.domain import Category, FavoredParty, Materiality
from redline_agent.infra.llm.interpreter import (
    Interpretation,
    InterpretationRequest,
)

_CATEGORIES = ", ".join(c.value for c in Category)

_SYSTEM_PROMPT = (
    "You are a contract-analysis assistant producing attorney work-product for "
    "review. You are given the exact before/after text of one clause-level "
    "change that a deterministic diff already detected, and the name of the "
    "party the user represents. Explain only what this change means; never "
    "assert legal conclusions. Respond with a JSON object with keys:\n"
    '- "summary": a one- or two-sentence plain-English description of what '
    "changed.\n"
    '- "materiality": "substantive" or "cosmetic" ("cosmetic" means '
    "formatting/wording with no change in meaning or effect).\n"
    f'- "category": one of {_CATEGORIES} (use "other" if none fit).\n'
    '- "favored_party": "represented" if the change benefits the represented '
    'party, "counterparty" if it benefits the other side, or "neutral".\n'
    '- "risk_flag": if the change is unusual or aggressive, a short sentence '
    "prompting the attorney to review it (framed as a review prompt, never a "
    'conclusion); otherwise null.'
)


def _user_prompt(request: InterpretationRequest) -> str:
    return (
        f"Represented party: {request.represented_party or '(unspecified)'}\n"
        f"Change type: {request.change_type.value}\n"
        f"Before:\n{request.raw_before or '(none)'}\n\n"
        f"After:\n{request.raw_after or '(none)'}"
    )


class AzureOpenAIInterpreter:
    """Interprets a change with an Azure OpenAI chat deployment."""

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = "2024-06-01",
    ) -> None:
        self._api_key = api_key
        self._endpoint = endpoint
        self._deployment = deployment
        self._api_version = api_version
        self._client = None

    @property
    def model_name(self) -> str:
        return self._deployment

    def _get_client(self):
        if self._client is None:
            from openai import AsyncAzureOpenAI  # lazy: optional dependency

            self._client = AsyncAzureOpenAI(
                api_key=self._api_key,
                azure_endpoint=self._endpoint,
                api_version=self._api_version,
            )
        return self._client

    async def interpret(self, request: InterpretationRequest) -> Interpretation:
        client = self._get_client()
        response = await client.chat.completions.create(
            model=self._deployment,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": _user_prompt(request)},
            ],
        )
        data = json.loads(response.choices[0].message.content or "{}")
        category = data.get("category")
        favored_party = data.get("favored_party")
        risk_flag = data.get("risk_flag")
        return Interpretation(
            summary=data["summary"],
            materiality=Materiality(data["materiality"]),
            category=Category(category) if category else None,
            favored_party=FavoredParty(favored_party) if favored_party else None,
            risk_flag=risk_flag or None,
        )
