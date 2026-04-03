from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import logging
from typing import Any, Callable
from urllib.parse import urlparse

from rfp_rag_assistant.config import ChromaSettings
from rfp_rag_assistant.embeddings.base import Embedder
from rfp_rag_assistant.embeddings.chroma_schema import ChromaRecord, chunk_to_chroma_record
from rfp_rag_assistant.models import Chunk


def _build_chroma_client(settings: ChromaSettings) -> Any:
    try:
        import chromadb
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'chromadb' package is required to use ChromaIndexer. "
            "Install project dependencies to enable vector indexing."
        ) from exc

    if settings.api_key and settings.tenant and settings.database:
        return chromadb.CloudClient(
            api_key=settings.api_key,
            tenant=settings.tenant,
            database=settings.database,
        )

    if settings.endpoint:
        parsed = urlparse(settings.endpoint)
        host = parsed.hostname or parsed.path or settings.endpoint
        ssl = parsed.scheme == "https"
        port = parsed.port or (443 if ssl else 8000)
        kwargs: dict[str, Any] = {
            "host": host,
            "port": port,
            "ssl": ssl,
        }
        if settings.tenant:
            kwargs["tenant"] = settings.tenant
        if settings.database:
            kwargs["database"] = settings.database
        return chromadb.HttpClient(**kwargs)

    return chromadb.Client()


@dataclass(slots=True, frozen=True)
class IndexedCollectionResult:
    document_type: str
    collection_name: str
    chunk_count: int


@dataclass(slots=True, frozen=True)
class IndexingSummary:
    total_chunks: int
    collections: tuple[IndexedCollectionResult, ...]


@dataclass(slots=True)
class ChromaIndexer:
    settings: ChromaSettings
    embedder: Embedder
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    client_factory: Callable[[ChromaSettings], Any] | None = None
    _client: Any | None = field(init=False, default=None)

    def is_configured(self) -> bool:
        return bool((self.settings.namespace or "").strip())

    def collection_name_for(self, document_type: str) -> str:
        document = _slug(document_type)
        namespace = _slug(self.settings.namespace) or "dev"
        base = _slug(self.settings.collection)
        if base in {"", "rfp_answers"}:
            return f"{namespace}_{document}"
        return f"{namespace}_{base}_{document}"

    def upsert_chunks(self, chunks: list[Chunk]) -> IndexingSummary:
        if not chunks:
            return IndexingSummary(total_chunks=0, collections=())

        grouped: dict[str, list[Chunk]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.metadata.document_type].append(chunk)

        results: list[IndexedCollectionResult] = []
        for document_type, group in grouped.items():
            collection_name = self.collection_name_for(document_type)
            records = [chunk_to_chroma_record(chunk) for chunk in group]
            embeddings = self.embedder.embed(group)
            if len(embeddings) != len(records):
                raise ValueError(
                    f"Embedding count mismatch for {document_type}: "
                    f"records={len(records)} embeddings={len(embeddings)}"
                )

            collection = self._client_instance().get_or_create_collection(name=collection_name)
            collection.upsert(
                ids=[record.record_id for record in records],
                documents=[record.document for record in records],
                metadatas=[record.metadata for record in records],
                embeddings=embeddings,
            )
            self.logger.info(
                "Indexed %s chunks into Chroma collection %s",
                len(records),
                collection_name,
            )
            results.append(
                IndexedCollectionResult(
                    document_type=document_type,
                    collection_name=collection_name,
                    chunk_count=len(records),
                )
            )

        return IndexingSummary(
            total_chunks=len(chunks),
            collections=tuple(results),
        )

    def _client_instance(self) -> Any:
        if self._client is None:
            factory = self.client_factory or _build_chroma_client
            self._client = factory(self.settings)
        return self._client


def _slug(value: str) -> str:
    normalised = "".join(character.lower() if character.isalnum() else "_" for character in value.strip())
    return _collapse_underscores(normalised).strip("_")


def _collapse_underscores(value: str) -> str:
    while "__" in value:
        value = value.replace("__", "_")
    return value
