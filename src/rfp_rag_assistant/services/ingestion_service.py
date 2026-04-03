from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import tempfile
from typing import Any

from rfp_rag_assistant.embeddings import IndexingSummary
from rfp_rag_assistant.loaders.base import LoadedDocument
from rfp_rag_assistant.models import Chunk, MasterRFPMetadata


@dataclass(slots=True, frozen=True)
class IngestedDocumentResult:
    source_file: Path
    document_type: str
    section_count: int
    chunk_count: int


@dataclass(slots=True, frozen=True)
class IngestionSummary:
    document_count: int
    chunk_count: int
    indexing: IndexingSummary
    documents: tuple[IngestedDocumentResult, ...]


@dataclass(slots=True)
class IngestionService:
    blob_document_loader: Any
    parsers: dict[str, Any]
    chunkers: dict[str, Any]
    chroma_indexer: Any
    master_metadata: MasterRFPMetadata | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def ingest_blob_documents(self, *, limit: int | None = None) -> IngestionSummary:
        source_files = self.blob_document_loader.list_documents()
        if limit is not None:
            source_files = source_files[:limit]

        all_chunks: list[Chunk] = []
        document_results: list[IngestedDocumentResult] = []

        for source_file in source_files:
            loaded = self.blob_document_loader.load(source_file)
            document_result, chunks = self.ingest_loaded_document(loaded)
            document_results.append(document_result)
            all_chunks.extend(chunks)

        indexing = self.chroma_indexer.upsert_chunks(all_chunks)
        summary = IngestionSummary(
            document_count=len(document_results),
            chunk_count=len(all_chunks),
            indexing=indexing,
            documents=tuple(document_results),
        )
        self.logger.info(
            "Completed blob ingestion documents=%s chunks=%s collections=%s",
            summary.document_count,
            summary.chunk_count,
            len(summary.indexing.collections),
        )
        return summary

    def ingest_loaded_document(self, loaded_document: LoadedDocument) -> tuple[IngestedDocumentResult, list[Chunk]]:
        document_type = self._document_type_for_path(loaded_document.source_file)
        parser = self._parser_for(document_type)
        chunker = self._chunker_for(document_type)
        staged_document = self._stage_for_parser(loaded_document)
        parsed = parser.parse(staged_document)
        chunks = chunker.chunk(parsed)
        self._apply_master_metadata(chunks)
        result = IngestedDocumentResult(
            source_file=loaded_document.source_file,
            document_type=document_type,
            section_count=len(parsed.sections),
            chunk_count=len(chunks),
        )
        self.logger.info(
            "Ingested document file=%s document_type=%s sections=%s chunks=%s",
            loaded_document.source_file.as_posix(),
            document_type,
            result.section_count,
            result.chunk_count,
        )
        return result, chunks

    def _apply_master_metadata(self, chunks: list[Chunk]) -> None:
        if self.master_metadata is None:
            return
        for chunk in chunks:
            metadata = chunk.metadata
            if not metadata.issuing_authority:
                metadata.issuing_authority = self.master_metadata.issuing_authority
            if not metadata.customer:
                metadata.customer = self.master_metadata.customer or self.master_metadata.issuing_authority
            if not metadata.rfp_id:
                metadata.rfp_id = self.master_metadata.rfp_id
            if not metadata.rfp_title:
                metadata.rfp_title = self.master_metadata.rfp_title
            if not metadata.region:
                metadata.region = self.master_metadata.region
            if not metadata.product_or_service_area:
                metadata.product_or_service_area = self.master_metadata.product_or_service_area

            if metadata.issuing_authority:
                chunk.structured_content.setdefault("issuing_authority", metadata.issuing_authority)
            if metadata.customer:
                chunk.structured_content.setdefault("customer", metadata.customer)
            if metadata.rfp_id:
                chunk.structured_content.setdefault("rfp_id", metadata.rfp_id)
            if metadata.rfp_title:
                chunk.structured_content.setdefault("rfp_title", metadata.rfp_title)

    def _document_type_for_path(self, source_file: Path) -> str:
        if not source_file.parts:
            raise ValueError(f"Cannot infer document_type from empty source path: {source_file}")
        document_type = source_file.parts[0]
        if document_type not in self.parsers:
            raise ValueError(f"Unsupported document_type inferred from source path: {document_type}")
        return document_type

    def _parser_for(self, document_type: str) -> Any:
        parser = self.parsers.get(document_type)
        if parser is None:
            raise ValueError(f"No parser configured for document_type: {document_type}")
        return parser

    def _chunker_for(self, document_type: str) -> Any:
        chunker = self.chunkers.get(document_type)
        if chunker is None:
            raise ValueError(f"No chunker configured for document_type: {document_type}")
        return chunker

    def _stage_for_parser(self, loaded_document: LoadedDocument) -> LoadedDocument:
        payload = loaded_document.payload
        if isinstance(payload, (str, Path)):
            return loaded_document
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError(
                f"Unsupported loaded document payload type for parsing: {type(payload).__name__}"
            )

        temp_dir = tempfile.mkdtemp(prefix="rfp-ingest-")
        staged_path = Path(temp_dir) / loaded_document.source_file.name
        staged_path.write_bytes(bytes(payload))
        return LoadedDocument(
            source_file=loaded_document.source_file,
            file_type=loaded_document.file_type,
            payload=staged_path,
            metadata=dict(loaded_document.metadata),
        )
