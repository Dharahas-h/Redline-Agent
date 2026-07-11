"""AlignmentAdjudicator Protocol and a deterministic fake.

When the aligner cannot confidently pair a clause by structure or embedding
similarity — a genuinely ambiguous split/merge/move — it asks the adjudicator to
choose among a short list of candidate prior clauses. Like the interpreter, the
adjudicator is a Protocol (decision #7: the LLM is swappable) and only ever
*resolves an ambiguity the deterministic pipeline surfaced*; it never invents a
change (decision #1 — the differ remains the sole authority on what changed).

``FakeAdjudicator`` is the offline, deterministic stand-in used by tests. The
real Azure OpenAI implementation lives beside it and imports its client lazily.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from redline_agent.config import Settings


@dataclass
class AdjudicationRequest:
    """One ambiguous current clause and its candidate prior clauses.

    ``candidates`` are the plausible prior-round clause texts, best-first. The
    adjudicator returns the index of its choice, or ``None`` if it judges the
    current clause to have no prior counterpart (a genuine addition).
    """

    curr_text: str
    candidates: list[str]


@dataclass
class AdjudicationResult:
    """The adjudicator's decision for one ambiguous clause."""

    choice: int | None
    confidence: float


class AlignmentAdjudicator(Protocol):
    """Resolves an ambiguous clause pairing. Swappable per decision #7."""

    @property
    def model_name(self) -> str:
        ...

    async def adjudicate(self, request: AdjudicationRequest) -> AdjudicationResult:
        """Pick the best candidate index, or ``None`` for no prior match."""
        ...


class FakeAdjudicator:
    """Deterministic, offline ``AlignmentAdjudicator`` for tests and local dev.

    Returns a fixed ``choice`` (default: the best-ranked candidate, index 0) with
    a fixed ``confidence``, and records requests so tests can assert the fallback
    fired. Confidence defaults low, so an adjudicated pairing is flagged for human
    review (the human-in-the-loop trust model, decision #5).
    """

    def __init__(
        self,
        choice: int | None = 0,
        confidence: float = 0.5,
        model_name: str = "fake-adjudicator",
    ) -> None:
        self._choice = choice
        self._confidence = confidence
        self._model_name = model_name
        self.calls = 0
        self.requests: list[AdjudicationRequest] = []

    @property
    def model_name(self) -> str:
        return self._model_name

    async def adjudicate(self, request: AdjudicationRequest) -> AdjudicationResult:
        self.calls += 1
        self.requests.append(request)
        choice = self._choice
        if choice is not None and choice >= len(request.candidates):
            choice = None
        return AdjudicationResult(choice=choice, confidence=self._confidence)


_SYSTEM_PROMPT = (
    "You are a contract-analysis assistant aligning clauses across two rounds of "
    "a negotiation. You are given the text of one current-round clause and a "
    "numbered list of candidate prior-round clauses it might correspond to. "
    "Choose the single best match. Respond with a JSON object with keys:\n"
    '- "choice": the 0-based index of the best candidate, or null if the current '
    "clause has no counterpart in the list (it is genuinely new).\n"
    '- "confidence": a number from 0 to 1 for how certain the match is.'
)


def _user_prompt(request: AdjudicationRequest) -> str:
    candidates = "\n".join(
        f"[{i}] {text}" for i, text in enumerate(request.candidates)
    )
    return (
        f"Current clause:\n{request.curr_text}\n\n"
        f"Candidate prior clauses:\n{candidates}"
    )


class AzureOpenAIAdjudicator:
    """Adjudicates an ambiguous pairing with an Azure OpenAI chat deployment."""

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

    async def adjudicate(self, request: AdjudicationRequest) -> AdjudicationResult:
        import json

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
        choice = data.get("choice")
        return AdjudicationResult(
            choice=int(choice) if choice is not None else None,
            confidence=float(data.get("confidence", 0.5)),
        )


def build_adjudicator(settings: Settings) -> AlignmentAdjudicator | None:
    """Construct the default adjudicator for the given settings.

    Uses Azure OpenAI when a chat deployment is configured; otherwise returns
    ``None``. With no adjudicator, the aligner keeps its best embedding guess for
    ambiguous clauses but flags it low-confidence for human review, rather than
    letting a stand-in model silently decide (decision #5).
    """
    if (
        settings.azure_openai_api_key
        and settings.azure_openai_endpoint
        and settings.azure_openai_deployment
    ):
        return AzureOpenAIAdjudicator(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )
    return None
