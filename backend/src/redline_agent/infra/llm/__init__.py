"""LLM Protocols and implementations (decision #7: swappable behind a Protocol).

``build_interpreter`` picks the OpenAI-compatible implementation when a key and
model are configured, and otherwise falls back to the deterministic
``FakeInterpreter`` so the service runs offline in local dev (mirroring the
SQLite fallback for the database — an environment convenience, not a scope
change).
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
    if settings.openai_api_key and settings.openai_model:
        from redline_agent.infra.llm.openai_chat import OpenAIInterpreter

        return OpenAIInterpreter(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    return FakeInterpreter()
