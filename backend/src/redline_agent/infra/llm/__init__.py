"""LLM Protocols and implementations (decision #7: swappable behind a Protocol).

``build_interpreter`` picks the Azure OpenAI implementation when it is
configured, and otherwise falls back to the deterministic ``FakeInterpreter``
so the service runs offline in local dev (mirroring the SQLite fallback for the
database — an environment convenience, not a scope change).
"""

from __future__ import annotations

from redline_agent.config import Settings
from redline_agent.infra.llm.interpreter import (
    FakeInterpreter,
    Interpretation,
    InterpretationRequest,
    LLMInterpreter,
)

__all__ = [
    "FakeInterpreter",
    "Interpretation",
    "InterpretationRequest",
    "LLMInterpreter",
    "build_interpreter",
]


def build_interpreter(settings: Settings) -> LLMInterpreter:
    """Construct the default interpreter for the given settings."""
    if (
        settings.azure_openai_api_key
        and settings.azure_openai_endpoint
        and settings.azure_openai_deployment
    ):
        from redline_agent.infra.llm.azure_openai import AzureOpenAIInterpreter

        return AzureOpenAIInterpreter(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
        )
    return FakeInterpreter()
