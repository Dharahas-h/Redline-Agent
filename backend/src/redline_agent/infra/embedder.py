"""Embedder Protocol and implementations (decision #7: swappable behind a Protocol).

The embedder turns clause text into a vector so the aligner can measure clause
similarity across rounds. It is a Protocol so the provider is swappable and
benchmarked before the default is locked; the default embeddings are Azure
``text-embedding-3-large``.

``FakeEmbedder`` is the deterministic, offline stand-in used by tests and by
local dev when no provider is configured (mirroring the ``FakeInterpreter`` and
SQLite fallbacks — an environment convenience, not a scope change). It embeds a
whole batch against a shared bag-of-words vocabulary, so cosine similarity
reflects lexical overlap deterministically and without hash collisions.
"""

from __future__ import annotations

import re
from typing import Protocol

from redline_agent.config import Settings

_TOKEN = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall((text or "").lower())


class Embedder(Protocol):
    """Turns text into vectors. Swappable per decision #7."""

    @property
    def model_name(self) -> str:
        """Identifier of the embedding model/deployment."""
        ...

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in order."""
        ...


class FakeEmbedder:
    """Deterministic, offline ``Embedder`` for tests and local dev.

    A batch is embedded against a vocabulary built from the whole batch, so each
    distinct token gets its own dimension: cosine similarity between two vectors
    is exactly their lexical (bag-of-words) overlap, with no hash collisions.
    Never touches the network.
    """

    def __init__(self, model_name: str = "fake-embedder") -> None:
        self._model_name = model_name
        self.calls = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        vocab: dict[str, int] = {}
        for text in texts:
            for token in _tokens(text):
                if token not in vocab:
                    vocab[token] = len(vocab)
        dim = len(vocab)
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * dim
            for token in _tokens(text):
                vec[vocab[token]] += 1.0
            vectors.append(vec)
        return vectors


class AzureEmbedder:
    """Azure OpenAI implementation of the ``Embedder`` Protocol.

    The default embeddings in deployment (decision #7). Never exercised by tests
    (no test hits the network — ``FakeEmbedder`` stands in); the ``openai``
    client is imported lazily so this module imports cleanly without it.
    """

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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        client = self._get_client()
        response = await client.embeddings.create(
            model=self._deployment, input=texts
        )
        return [item.embedding for item in response.data]


def build_embedder(settings: Settings) -> Embedder:
    """Construct the default embedder for the given settings.

    Uses Azure when an embedding deployment is configured; otherwise falls back
    to the deterministic offline ``FakeEmbedder``.
    """
    if (
        settings.azure_openai_api_key
        and settings.azure_openai_endpoint
        and settings.azure_openai_embedding_deployment
    ):
        return AzureEmbedder(
            api_key=settings.azure_openai_api_key,
            endpoint=settings.azure_openai_endpoint,
            deployment=settings.azure_openai_embedding_deployment,
            api_version=settings.azure_openai_api_version,
        )
    return FakeEmbedder()
