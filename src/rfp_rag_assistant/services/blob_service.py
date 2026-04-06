from __future__ import annotations

import mimetypes
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from rfp_rag_assistant.config import AppSettings


class AzureBlobDependencyMissingError(RuntimeError):
    """Raised when Azure Blob support is configured but the SDK is unavailable."""


class BlobClientFactory(Protocol):
    def __call__(self, connection_string: str) -> Any: ...


@dataclass(slots=True)
class BlobService:
    settings: AppSettings
    client_factory: BlobClientFactory | None = None
    _client: Any | None = field(default=None, init=False, repr=False)

    def is_configured(self) -> bool:
        storage = self.settings.azure_storage
        return bool(storage.account and storage.key)

    def connection_string(self) -> str:
        storage = self.settings.azure_storage
        if not self.is_configured():
            raise RuntimeError("Azure Blob storage is not configured.")
        return (
            "DefaultEndpointsProtocol=https;"
            f"AccountName={storage.account};"
            f"AccountKey={storage.key};"
            "EndpointSuffix=core.windows.net"
        )

    def _default_client_factory(self) -> BlobClientFactory:  # pragma: no cover - SDK-dependent
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:  # pragma: no cover - depends on local package install
            raise AzureBlobDependencyMissingError(
                "Install 'azure-storage-blob' to use Azure Blob storage."
            ) from exc

        return BlobServiceClient.from_connection_string

    def build_client(self):
        if not self.is_configured():
            raise RuntimeError("Azure Blob storage is not configured.")

        if self._client is None:
            factory = self.client_factory or self._default_client_factory()
            self._client = factory(self.connection_string())
        return self._client

    def container_client(self, container_name: str) -> Any:
        return self.build_client().get_container_client(container_name)

    def container_exists(self, container_name: str) -> bool:
        return bool(self.container_client(container_name).exists())

    def list_blob_names(self, container_name: str, *, prefix: str = "") -> list[str]:
        container = self.container_client(container_name)
        return [blob.name for blob in container.list_blobs(name_starts_with=prefix)]

    def get_blob_properties(self, container_name: str, blob_name: str) -> dict[str, Any]:
        blob_client = self.container_client(container_name).get_blob_client(blob_name)
        properties = blob_client.get_blob_properties()
        return {
            "etag": _normalise_etag(getattr(properties, "etag", None)),
            "last_modified": _normalise_datetime(getattr(properties, "last_modified", None)),
            "content_length": getattr(properties, "size", None),
        }

    def download_blob_bytes(self, container_name: str, blob_name: str) -> bytes:
        blob_client = self.container_client(container_name).get_blob_client(blob_name)
        return bytes(blob_client.download_blob().readall())

    def download_blob_to_file(self, container_name: str, blob_name: str, local_path: Path) -> Path:
        payload = self.download_blob_bytes(container_name, blob_name)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(payload)
        return local_path

    def upload_blob_bytes(
        self,
        container_name: str,
        blob_name: str,
        payload: bytes,
        *,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> None:
        container = self.container_client(container_name)
        container.upload_blob(
            name=blob_name,
            data=payload,
            overwrite=overwrite,
            metadata=metadata,
            content_type=content_type,
        )

    def upload_file_to_blob(
        self,
        container_name: str,
        local_path: Path,
        *,
        blob_name: str | None = None,
        relative_to: Path | None = None,
        overwrite: bool = False,
        metadata: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> str:
        target_blob_name = self.resolve_blob_name(local_path, blob_name=blob_name, relative_to=relative_to)
        guessed_content_type, _ = mimetypes.guess_type(str(local_path))
        self.upload_blob_bytes(
            container_name,
            target_blob_name,
            local_path.read_bytes(),
            overwrite=overwrite,
            metadata=metadata,
            content_type=content_type or guessed_content_type,
        )
        return target_blob_name

    @staticmethod
    def blob_path(*parts: str) -> str:
        return "/".join(part.strip("/") for part in parts if part and part.strip("/"))

    def resolve_blob_name(
        self,
        local_path: Path,
        *,
        blob_name: str | None = None,
        relative_to: Path | None = None,
    ) -> str:
        if blob_name:
            return blob_name
        if relative_to is not None:
            return local_path.relative_to(relative_to).as_posix()
        if not local_path.is_absolute():
            return local_path.as_posix()
        return local_path.name


def _normalise_etag(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    return text


def _normalise_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return None
