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

from redline_agent.domain import Materiality
from redline_agent.infra.llm.interpreter import (
    Interpretation,
    InterpretationRequest,
)

_SYSTEM_PROMPT = (
    "You are a contract-analysis assistant producing attorney work-product for "
    "review. You are given the exact before/after text of one clause-level "
    "change that a deterministic diff already detected. Explain only what this "
    "change means; never assert legal conclusions. Respond with a JSON object "
    'with keys "summary" (a one- or two-sentence plain-English description of '
    'what changed) and "materiality" (either "substantive" or "cosmetic", where '
    '"cosmetic" means formatting/wording with no change in meaning or effect).'
)


def _user_prompt(request: InterpretationRequest) -> str:
    return (
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
        return Interpretation(
            summary=data["summary"],
            materiality=Materiality(data["materiality"]),
        )
