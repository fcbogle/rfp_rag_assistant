from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rfp_rag_assistant.source_paths import infer_document_type_from_path


@dataclass(slots=True, frozen=True)
class ReconciledSourceStatus:
    source_file: Path
    document_type: str
    file_type: str
    support_status: str
    ingestion_status: str
    chunk_count: int
    blob_name: str
    blob_etag: str | None = None
    blob_last_modified: datetime | None = None
    blob_content_length: int | None = None
    indexed_blob_etag: str | None = None
    indexed_blob_last_modified: str | None = None
    indexed_ingested_at: str | None = None
    collection_name: str | None = None


@dataclass(slots=True, frozen=True)
class ReconciliationSnapshot:
    items: tuple[ReconciledSourceStatus, ...]
    blob_file_count: int
    indexed_source_count: int
    collections_scanned: tuple[str, ...]


@dataclass(slots=True)
class ReconciliationService:
    blob_document_loader: Any
    blob_service: Any
    chroma_indexer: Any
    supported_extensions: tuple[str, ...] = (".docx", ".xlsx", ".pdf")

    def list_source_status(
        self,
        *,
        document_types: list[str] | None = None,
    ) -> tuple[ReconciledSourceStatus, ...]:
        return self.build_snapshot(document_types=document_types).items

    def build_snapshot(
        self,
        *,
        document_types: list[str] | None = None,
    ) -> ReconciliationSnapshot:
        source_files = self.blob_document_loader.list_documents()
        indexed_sources = self.chroma_indexer.list_indexed_sources(document_types=document_types)
        allowed = set(document_types or [])
        items: list[ReconciledSourceStatus] = []

        for source_file in source_files:
            document_type = infer_document_type_from_path(source_file)
            if allowed and document_type not in allowed:
                continue

            support_status = _support_status_for_path(source_file)
            blob_name = source_file.as_posix()
            blob_properties = self.blob_service.get_blob_properties(
                self.blob_document_loader.container_name,
                blob_name,
            )
            indexed = indexed_sources.get(blob_name)
            ingestion_status = _derive_ingestion_status(
                support_status=support_status,
                blob_etag=blob_properties.get("etag"),
                indexed=indexed,
            )
            items.append(
                ReconciledSourceStatus(
                    source_file=source_file,
                    document_type=document_type,
                    file_type=source_file.suffix.lstrip(".").lower(),
                    support_status=support_status,
                    ingestion_status=ingestion_status,
                    chunk_count=int(indexed.get("chunk_count", 0) if indexed else 0),
                    blob_name=blob_name,
                    blob_etag=_as_optional_string(blob_properties.get("etag")),
                    blob_last_modified=blob_properties.get("last_modified"),
                    blob_content_length=blob_properties.get("content_length"),
                    indexed_blob_etag=_as_optional_string(indexed.get("blob_etag")) if indexed else None,
                    indexed_blob_last_modified=_as_optional_string(indexed.get("blob_last_modified")) if indexed else None,
                    indexed_ingested_at=_as_optional_string(indexed.get("ingested_at")) if indexed else None,
                    collection_name=_as_optional_string(indexed.get("collection_name")) if indexed else None,
                )
            )

        collections_scanned = tuple(
            sorted(
                {
                    str(item.get("collection_name"))
                    for item in indexed_sources.values()
                    if item.get("collection_name")
                }
            )
        )
        return ReconciliationSnapshot(
            items=tuple(sorted(items, key=lambda item: (item.document_type, item.source_file.as_posix()))),
            blob_file_count=len(items),
            indexed_source_count=len(indexed_sources),
            collections_scanned=collections_scanned,
        )


def _derive_ingestion_status(
    *,
    support_status: str,
    blob_etag: str | None,
    indexed: dict[str, Any] | None,
) -> str:
    if support_status != "supported":
        return support_status
    if not indexed:
        return "not_ingested"
    indexed_etag = _as_optional_string(indexed.get("blob_etag"))
    if not indexed_etag or not blob_etag:
        return "stale"
    if indexed_etag != blob_etag:
        return "stale"
    return "ingested"


def _support_status_for_path(source_file: Path) -> str:
    suffix = source_file.suffix.lower()
    if suffix in {".docx", ".xlsx", ".pdf"}:
        return "supported"
    if suffix == ".pptx":
        return "unsupported"
    return "unknown"


def _as_optional_string(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
