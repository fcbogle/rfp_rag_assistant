from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
import logging
from pathlib import Path
import tempfile
import threading
from typing import Any
from uuid import uuid4

from rfp_rag_assistant.embeddings import IndexedCollectionResult, IndexingSummary
from rfp_rag_assistant.loaders.base import LoadedDocument
from rfp_rag_assistant.models import Chunk, MasterRFPMetadata
from rfp_rag_assistant.source_paths import infer_document_type_from_path


TERMINAL_JOB_STATUSES = {"completed", "completed_with_errors", "failed"}


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
class SourceIngestionStatus:
    source_file: Path
    document_type: str
    file_type: str
    support_status: str
    ingestion_status: str = "not_ingested"
    chunk_count: int = 0
    last_job_id: str | None = None
    last_error: str | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class IngestionJob:
    job_id: str
    status: str
    current_phase: str
    rfp_id: str | None
    submission_id: str | None
    document_types: tuple[str, ...]
    source_files: tuple[str, ...]
    limit: int | None
    total_documents: int
    processed_documents: int
    total_chunks: int
    indexing: IndexingSummary
    documents: tuple[IngestedDocumentResult, ...]
    errors: tuple[str, ...]
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(slots=True)
class IngestionService:
    blob_document_loader: Any
    parsers: dict[str, Any]
    chunkers: dict[str, Any]
    chroma_indexer: Any
    master_metadata: MasterRFPMetadata | None = None
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    _jobs: dict[str, IngestionJob] = field(init=False, default_factory=dict)
    _source_status: dict[tuple[str | None, str | None, str], SourceIngestionStatus] = field(
        init=False,
        default_factory=dict,
    )
    _active_job_ids_by_scope: dict[tuple[str | None, str | None], str] = field(
        init=False,
        default_factory=dict,
    )

    def ingest_blob_documents(
        self,
        *,
        limit: int | None = None,
        document_types: list[str] | None = None,
        master_metadata: MasterRFPMetadata | None = None,
        rfp_id: str | None = None,
        submission_id: str | None = None,
        source_files: list[str] | None = None,
    ) -> IngestionSummary:
        resolved_master = master_metadata or self.master_metadata
        selected_source_files = self._resolve_source_files(
            limit=limit,
            document_types=document_types,
            source_files=source_files,
        )
        return self._ingest_source_files(
            selected_source_files,
            master_metadata=resolved_master,
            rfp_id=rfp_id,
            submission_id=submission_id,
            job_id=None,
        )

    def submit_job(
        self,
        *,
        limit: int | None = None,
        document_types: list[str] | None = None,
        source_files: list[str] | None = None,
        master_metadata: MasterRFPMetadata | None = None,
        rfp_id: str | None = None,
        submission_id: str | None = None,
    ) -> IngestionJob:
        selected_source_files = self._resolve_source_files(
            limit=limit,
            document_types=document_types,
            source_files=source_files,
        )
        resolved_master = master_metadata or self.master_metadata
        resolved_document_types = tuple(
            sorted(
                {
                    self._document_type_for_path(source_file)
                    for source_file in selected_source_files
                }
            )
        )
        job = IngestionJob(
            job_id=uuid4().hex,
            status="queued",
            current_phase="queued",
            rfp_id=rfp_id,
            submission_id=submission_id,
            document_types=tuple(document_types or resolved_document_types),
            source_files=tuple(source_file.as_posix() for source_file in selected_source_files),
            limit=limit,
            total_documents=len(selected_source_files),
            processed_documents=0,
            total_chunks=0,
            indexing=IndexingSummary(total_chunks=0, collections=()),
            documents=(),
            errors=(),
            created_at=datetime.now(UTC),
        )
        scope_key = (rfp_id, submission_id)
        with self._lock:
            self._jobs[job.job_id] = job
            self._active_job_ids_by_scope[scope_key] = job.job_id

        worker = threading.Thread(
            target=self._run_job,
            kwargs={
                "job_id": job.job_id,
                "source_files": selected_source_files,
                "master_metadata": resolved_master,
                "rfp_id": rfp_id,
                "submission_id": submission_id,
            },
            daemon=True,
        )
        worker.start()
        return self.get_job(job.job_id) or job

    def get_job(self, job_id: str) -> IngestionJob | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return replace(job) if job else None

    def get_active_job(
        self,
        *,
        rfp_id: str | None = None,
        submission_id: str | None = None,
    ) -> IngestionJob | None:
        with self._lock:
            job_id = self._active_job_ids_by_scope.get((rfp_id, submission_id))
        if not job_id:
            return None
        return self.get_job(job_id)

    def list_source_status(
        self,
        *,
        rfp_id: str | None = None,
        submission_id: str | None = None,
        document_types: list[str] | None = None,
    ) -> tuple[SourceIngestionStatus, ...]:
        source_files = self._resolve_source_files(limit=None, document_types=document_types, source_files=None)
        items: list[SourceIngestionStatus] = []
        for source_file in source_files:
            status = self._ensure_source_status(
                source_file,
                rfp_id=rfp_id,
                submission_id=submission_id,
            )
            items.append(status)
        return tuple(
            sorted(
                (replace(item) for item in items),
                key=lambda item: (item.document_type, item.source_file.as_posix()),
            )
        )

    def ingest_loaded_document(
        self,
        loaded_document: LoadedDocument,
        *,
        master_metadata: MasterRFPMetadata | None = None,
    ) -> tuple[IngestedDocumentResult, list[Chunk]]:
        document_type = self._document_type_for_path(loaded_document.source_file)
        parser = self._parser_for(document_type)
        chunker = self._chunker_for(document_type)
        staged_document = self._stage_for_parser(loaded_document)
        parsed = parser.parse(staged_document)
        self._normalize_parsed_document_provenance(parsed, loaded_document)
        chunks = chunker.chunk(parsed)
        self._normalize_chunk_provenance(chunks, loaded_document)
        self._apply_loaded_document_metadata(chunks, loaded_document)
        self._apply_master_metadata(chunks, master_metadata=master_metadata)
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

    def _ingest_source_files(
        self,
        source_files: list[Path],
        *,
        master_metadata: MasterRFPMetadata | None,
        rfp_id: str | None,
        submission_id: str | None,
        job_id: str | None,
    ) -> IngestionSummary:
        document_results: list[IngestedDocumentResult] = []
        collection_counts: dict[tuple[str, str], int] = defaultdict(int)
        total_chunks = 0

        for source_file in source_files:
            loaded = self.blob_document_loader.load(source_file)
            document_result, chunks = self.ingest_loaded_document(
                loaded,
                master_metadata=master_metadata,
            )
            indexing = self.chroma_indexer.upsert_chunks(chunks)
            for item in indexing.collections:
                collection_counts[(item.document_type, item.collection_name)] += item.chunk_count
            total_chunks += len(chunks)
            document_results.append(document_result)
            if job_id is not None:
                self._mark_source_ingested(
                    source_file,
                    chunk_count=document_result.chunk_count,
                    job_id=job_id,
                    rfp_id=rfp_id,
                    submission_id=submission_id,
                )

        indexing = IndexingSummary(
            total_chunks=total_chunks,
            collections=tuple(
                IndexedCollectionResult(
                    document_type=document_type,
                    collection_name=collection_name,
                    chunk_count=chunk_count,
                )
                for (document_type, collection_name), chunk_count in sorted(collection_counts.items())
            ),
        )
        summary = IngestionSummary(
            document_count=len(document_results),
            chunk_count=total_chunks,
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

    def _run_job(
        self,
        *,
        job_id: str,
        source_files: list[Path],
        master_metadata: MasterRFPMetadata | None,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> None:
        self._update_job(
            job_id,
            status="running",
            current_phase="preparing_documents",
            started_at=datetime.now(UTC),
        )
        errors: list[str] = []
        document_results: list[IngestedDocumentResult] = []
        collection_counts: dict[tuple[str, str], int] = defaultdict(int)
        total_chunks = 0

        if not source_files:
            self._complete_job(
                job_id,
                documents=document_results,
                collection_counts=collection_counts,
                total_chunks=0,
                errors=[],
            )
            return

        for index, source_file in enumerate(source_files, start=1):
            self._update_job(
                job_id,
                current_phase=f"processing {index} of {len(source_files)}",
            )
            self._mark_source_ingesting(
                source_file,
                job_id=job_id,
                rfp_id=rfp_id,
                submission_id=submission_id,
            )
            try:
                loaded = self.blob_document_loader.load(source_file)
                document_result, chunks = self.ingest_loaded_document(
                    loaded,
                    master_metadata=master_metadata,
                )
                indexing = self.chroma_indexer.upsert_chunks(chunks)
                for item in indexing.collections:
                    collection_counts[(item.document_type, item.collection_name)] += item.chunk_count
                total_chunks += len(chunks)
                document_results.append(document_result)
                self._mark_source_ingested(
                    source_file,
                    chunk_count=document_result.chunk_count,
                    job_id=job_id,
                    rfp_id=rfp_id,
                    submission_id=submission_id,
                )
            except Exception as exc:  # pragma: no cover - exercised operationally
                message = f"{source_file.as_posix()}: {exc}"
                errors.append(message)
                self.logger.exception("Ingestion job failed for %s", source_file.as_posix())
                self._mark_source_failed(
                    source_file,
                    error=str(exc),
                    job_id=job_id,
                    rfp_id=rfp_id,
                    submission_id=submission_id,
                )
            finally:
                self._update_job(
                    job_id,
                    processed_documents=index,
                    total_chunks=total_chunks,
                )

        self._complete_job(
            job_id,
            documents=document_results,
            collection_counts=collection_counts,
            total_chunks=total_chunks,
            errors=errors,
        )

    def _complete_job(
        self,
        job_id: str,
        *,
        documents: list[IngestedDocumentResult],
        collection_counts: dict[tuple[str, str], int],
        total_chunks: int,
        errors: list[str],
    ) -> None:
        collections = tuple(
            IndexedCollectionResult(
                document_type=document_type,
                collection_name=collection_name,
                chunk_count=chunk_count,
            )
            for (document_type, collection_name), chunk_count in sorted(collection_counts.items())
        )
        status = "completed"
        if errors:
            status = "completed_with_errors" if documents else "failed"
        completed_at = datetime.now(UTC)
        self._update_job(
            job_id,
            status=status,
            current_phase="completed" if status == "completed" else status,
            completed_at=completed_at,
            documents=tuple(documents),
            indexing=IndexingSummary(total_chunks=total_chunks, collections=collections),
            errors=tuple(errors),
            total_chunks=total_chunks,
        )
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                scope_key = (job.rfp_id, job.submission_id)
                if self._active_job_ids_by_scope.get(scope_key) == job_id:
                    self._active_job_ids_by_scope.pop(scope_key, None)

    def _update_job(self, job_id: str, **changes: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in changes.items():
                setattr(job, key, value)

    def _resolve_source_files(
        self,
        *,
        limit: int | None,
        document_types: list[str] | None,
        source_files: list[str] | None,
    ) -> list[Path]:
        available = self.blob_document_loader.list_documents()
        by_name = {path.as_posix(): path for path in available}

        if source_files:
            missing = [item for item in source_files if item not in by_name]
            if missing:
                raise ValueError(f"Unknown source_file requested for ingestion: {missing[0]}")
            resolved = [by_name[item] for item in source_files]
        else:
            resolved = list(available)

        if document_types:
            allowed = set(document_types)
            resolved = [
                source_file
                for source_file in resolved
                if self._document_type_for_path(source_file) in allowed
            ]

        if limit is not None:
            resolved = resolved[:limit]
        return resolved

    def _apply_master_metadata(
        self,
        chunks: list[Chunk],
        *,
        master_metadata: MasterRFPMetadata | None = None,
    ) -> None:
        resolved_master = master_metadata or self.master_metadata
        if resolved_master is None:
            return
        for chunk in chunks:
            metadata = chunk.metadata
            if not metadata.issuing_authority:
                metadata.issuing_authority = resolved_master.issuing_authority
            if not metadata.customer:
                metadata.customer = resolved_master.customer or resolved_master.issuing_authority
            if not metadata.rfp_id:
                metadata.rfp_id = resolved_master.rfp_id
            if not metadata.rfp_title:
                metadata.rfp_title = resolved_master.rfp_title
            if not metadata.region:
                metadata.region = resolved_master.region
            if not metadata.product_or_service_area:
                metadata.product_or_service_area = resolved_master.product_or_service_area

            if metadata.issuing_authority:
                chunk.structured_content.setdefault("issuing_authority", metadata.issuing_authority)
            if metadata.customer:
                chunk.structured_content.setdefault("customer", metadata.customer)
            if metadata.rfp_id:
                chunk.structured_content.setdefault("rfp_id", metadata.rfp_id)
            if metadata.rfp_title:
                chunk.structured_content.setdefault("rfp_title", metadata.rfp_title)

    def _apply_loaded_document_metadata(self, chunks: list[Chunk], loaded_document: LoadedDocument) -> None:
        ingested_at = datetime.now(UTC)
        blob_name = loaded_document.metadata.get("blob_name")
        blob_etag = loaded_document.metadata.get("blob_etag")
        blob_last_modified = loaded_document.metadata.get("blob_last_modified")
        blob_content_length = loaded_document.metadata.get("blob_content_length")
        for chunk in chunks:
            metadata = chunk.metadata
            if not metadata.blob_name:
                metadata.blob_name = str(blob_name) if blob_name else loaded_document.source_file.as_posix()
            if not metadata.blob_etag and blob_etag:
                metadata.blob_etag = str(blob_etag)
            if metadata.blob_last_modified is None and isinstance(blob_last_modified, datetime):
                metadata.blob_last_modified = blob_last_modified
            if metadata.blob_content_length is None and isinstance(blob_content_length, int):
                metadata.blob_content_length = blob_content_length
            if metadata.ingested_at is None:
                metadata.ingested_at = ingested_at

    def _normalize_parsed_document_provenance(
        self,
        parsed_document: Any,
        loaded_document: LoadedDocument,
    ) -> None:
        parsed_document.source_file = loaded_document.source_file
        parsed_document.file_type = loaded_document.file_type

    def _normalize_chunk_provenance(self, chunks: list[Chunk], loaded_document: LoadedDocument) -> None:
        canonical_source = loaded_document.source_file
        canonical_file_type = loaded_document.file_type
        canonical_document_type = self._document_type_for_path(canonical_source)
        for chunk in chunks:
            chunk.metadata.source_file = canonical_source
            chunk.metadata.file_type = canonical_file_type
            chunk.metadata.document_type = canonical_document_type
            if chunk.metadata.source_reference is not None:
                chunk.metadata.source_reference.source_file = canonical_source
                chunk.metadata.source_reference.file_type = canonical_file_type
                chunk.metadata.source_reference.document_type = canonical_document_type

    def _document_type_for_path(self, source_file: Path) -> str:
        document_type = infer_document_type_from_path(source_file)
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

    def _scope_key(self, *, rfp_id: str | None, submission_id: str | None) -> tuple[str | None, str | None]:
        return (rfp_id, submission_id)

    def _status_key(
        self,
        source_file: Path,
        *,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> tuple[str | None, str | None, str]:
        return (rfp_id, submission_id, source_file.as_posix())

    def _ensure_source_status(
        self,
        source_file: Path,
        *,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> SourceIngestionStatus:
        key = self._status_key(source_file, rfp_id=rfp_id, submission_id=submission_id)
        with self._lock:
            status = self._source_status.get(key)
            if status is None:
                status = SourceIngestionStatus(
                    source_file=source_file,
                    document_type=self._document_type_for_path(source_file),
                    file_type=source_file.suffix.lstrip(".").lower(),
                    support_status=_support_status_for_path(source_file),
                )
                self._source_status[key] = status
            return status

    def _mark_source_ingesting(
        self,
        source_file: Path,
        *,
        job_id: str,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> None:
        status = self._ensure_source_status(source_file, rfp_id=rfp_id, submission_id=submission_id)
        with self._lock:
            status.ingestion_status = "ingesting"
            status.last_job_id = job_id
            status.last_error = None
            status.updated_at = datetime.now(UTC)

    def _mark_source_ingested(
        self,
        source_file: Path,
        *,
        chunk_count: int,
        job_id: str,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> None:
        status = self._ensure_source_status(source_file, rfp_id=rfp_id, submission_id=submission_id)
        with self._lock:
            status.ingestion_status = "ingested"
            status.chunk_count = chunk_count
            status.last_job_id = job_id
            status.last_error = None
            status.updated_at = datetime.now(UTC)

    def _mark_source_failed(
        self,
        source_file: Path,
        *,
        error: str,
        job_id: str,
        rfp_id: str | None,
        submission_id: str | None,
    ) -> None:
        status = self._ensure_source_status(source_file, rfp_id=rfp_id, submission_id=submission_id)
        with self._lock:
            status.ingestion_status = "failed"
            status.last_job_id = job_id
            status.last_error = error
            status.updated_at = datetime.now(UTC)


def _support_status_for_path(source_file: Path) -> str:
    suffix = source_file.suffix.lower()
    if suffix in {".docx", ".xlsx", ".pdf"}:
        return "supported"
    if suffix == ".pptx":
        return "unsupported"
    return "unknown"
