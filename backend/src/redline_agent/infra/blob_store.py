"""BlobStore Protocol and its implementations.

Raw .docx files are stored by reference (rounds.blob_uri). The in-memory store
backs tests and local dev without touching the network; the Azure Blob store is
used whenever a connection string is configured.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from redline_agent.config import Settings


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


class AzureBlobStore:
    """BlobStore backed by an Azure Storage container.

    URIs use the ``azure://<container>/<key>`` scheme rather than the public
    blob URL so ``get`` can reconstruct a client from the connection string
    without relying on the blob being publicly readable. The container is
    created on first use if it does not already exist.
    """

    _SCHEME = "azure://"

    def __init__(self, connection_string: str, container: str) -> None:
        # Imported lazily so the SDK is only required when Azure is configured.
        from azure.storage.blob import BlobServiceClient

        self._container = container
        self._service = BlobServiceClient.from_connection_string(
            connection_string
        )
        self._container_client = self._service.get_container_client(container)
        self._ensure_container()

    def _ensure_container(self) -> None:
        from azure.core.exceptions import ResourceExistsError

        try:
            self._container_client.create_container()
        except ResourceExistsError:
            pass

    def put(self, key: str, data: bytes) -> str:
        self._container_client.upload_blob(name=key, data=data, overwrite=True)
        return f"{self._SCHEME}{self._container}/{key}"

    def get(self, uri: str) -> bytes:
        path = uri.removeprefix(self._SCHEME)
        _container, _, key = path.partition("/")
        blob = self._container_client.get_blob_client(key)
        return blob.download_blob().readall()


def build_blob_store(settings: Settings) -> BlobStore:
    """Return the Azure store when configured, else the in-memory store."""
    if settings.blob_connection_string:
        return AzureBlobStore(
            settings.blob_connection_string, settings.blob_container
        )
    return InMemoryBlobStore()
