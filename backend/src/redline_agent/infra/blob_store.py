"""BlobStore Protocol and an in-memory implementation.

Raw .docx files are stored by reference (rounds.blob_uri). The Azure Blob
implementation is a later swap; the in-memory store backs tests and local dev
without touching the network.
"""

from __future__ import annotations

from typing import Protocol


class BlobStore(Protocol):
    """Stores round .docx bytes and returns a URI to retrieve them by."""

    def put(self, key: str, data: bytes) -> str:
        """Store ``data`` under ``key`` and return its blob URI."""
        ...

    def get(self, uri: str) -> bytes:
        """Retrieve the bytes previously stored at ``uri``."""
        ...


class InMemoryBlobStore:
    """Process-local BlobStore for tests and single-process dev."""

    _SCHEME = "mem://"

    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}

    def put(self, key: str, data: bytes) -> str:
        self._data[key] = data
        return f"{self._SCHEME}{key}"

    def get(self, uri: str) -> bytes:
        key = uri.removeprefix(self._SCHEME)
        return self._data[key]
