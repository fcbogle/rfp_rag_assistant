from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from rfp_rag_assistant.corpus_info import build_corpus_info
from rfp_rag_assistant.models import MasterRFPMetadata
from rfp_rag_assistant.reference_urls import load_reference_url_inventory
from rfp_rag_assistant.rfp_scopes import list_rfp_scopes, resolve_scope
from rfp_rag_assistant.services.ingestion_service import TERMINAL_JOB_STATUSES

router = APIRouter()


class IngestionRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1)
    document_types: list[str] | None = None
    source_files: list[str] | None = None
    submission_id: str | None = None
    issuing_authority: str | None = None
    customer: str | None = None
    rfp_id: str | None = None
    rfp_title: str | None = None


@router.get("/health")
def get_health(request: Request) -> dict[str, bool]:
    return request.app.state.container.health_service.check()


@router.get("/rfp-scopes")
def get_rfp_scopes() -> dict[str, Any]:
    scopes = list_rfp_scopes()
    return {
        "scope_count": len(scopes),
        "scopes": scopes,
    }


@router.get("/documents")
def list_documents(
    request: Request,
    rfp_id: str | None = Query(default=None),
    submission_id: str | None = Query(default=None),
) -> dict[str, Any]:
    container = request.app.state.container
    scope = resolve_scope(rfp_id=rfp_id, submission_id=submission_id)
    if (rfp_id or submission_id) and scope is None:
        raise HTTPException(status_code=404, detail="Requested RFP/submission scope was not found")
    scope_kwargs = _scope_kwargs(scope)
    try:
        source_status_items = container.reconciliation_service.list_source_status()
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    items = [_source_status_payload(item) for item in source_status_items]
    counts: dict[str, int] = {}
    for item in items:
        counts[item["document_type"]] = counts.get(item["document_type"], 0) + 1

    return {
        "scope": scope,
        "container_name": container.blob_document_loader.container_name,
        "prefix": container.blob_document_loader.prefix,
        "document_count": len(items),
        "counts_by_document_type": counts,
        "documents": items,
    }


@router.get("/corpus-info")
def get_corpus_info(
    request: Request,
    rfp_id: str | None = Query(default=None),
    submission_id: str | None = Query(default=None),
) -> dict[str, Any]:
    container = request.app.state.container
    settings = request.app.state.settings
    scope = resolve_scope(rfp_id=rfp_id, submission_id=submission_id)
    if (rfp_id or submission_id) and scope is None:
        raise HTTPException(status_code=404, detail="Requested RFP/submission scope was not found")
    payload = build_corpus_info(settings, container.chroma_indexer)
    payload["scope"] = scope
    return payload


@router.get("/reference-urls")
def list_reference_urls(
    rfp_id: str | None = Query(default=None),
    submission_id: str | None = Query(default=None),
) -> dict[str, Any]:
    scope = resolve_scope(rfp_id=rfp_id, submission_id=submission_id)
    if (rfp_id or submission_id) and scope is None:
        raise HTTPException(status_code=404, detail="Requested RFP/submission scope was not found")
    items = load_reference_url_inventory()
    counts_by_document_type: dict[str, int] = {}
    counts_by_status: dict[str, int] = {}
    for item in items:
        document_type = str(item["document_type"])
        status = str(item["status"])
        counts_by_document_type[document_type] = counts_by_document_type.get(document_type, 0) + 1
        counts_by_status[status] = counts_by_status.get(status, 0) + 1
    return {
        "scope": scope,
        "reference_url_count": len(items),
        "counts_by_document_type": counts_by_document_type,
        "counts_by_status": counts_by_status,
        "items": items,
    }


@router.post("/ingestion")
def ingest_documents(request: Request, payload: IngestionRequest) -> dict[str, Any]:
    container = request.app.state.container
    master_metadata = _master_metadata_for_request(payload)
    container.ingestion_service.master_metadata = master_metadata

    try:
        summary = container.ingestion_service.ingest_blob_documents(
            limit=payload.limit,
            document_types=payload.document_types,
            source_files=payload.source_files,
            master_metadata=master_metadata,
            rfp_id=payload.rfp_id,
            submission_id=payload.submission_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return _summary_payload(summary, master_metadata=master_metadata)


@router.get("/ingestion/source-status")
def get_source_ingestion_status(
    request: Request,
    rfp_id: str | None = Query(default=None),
    submission_id: str | None = Query(default=None),
) -> dict[str, Any]:
    container = request.app.state.container
    scope = resolve_scope(rfp_id=rfp_id, submission_id=submission_id)
    if (rfp_id or submission_id) and scope is None:
        raise HTTPException(status_code=404, detail="Requested RFP/submission scope was not found")
    scope_kwargs = _scope_kwargs(scope)
    try:
        items = container.reconciliation_service.list_source_status()
        active_job = container.ingestion_service.get_active_job(**scope_kwargs)
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    status_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    payload_items = []
    for item in items:
        payload = _source_status_payload(item, active_job=active_job)
        type_counts[item.document_type] = type_counts.get(item.document_type, 0) + 1
        status_counts[payload["ingestion_status"]] = status_counts.get(payload["ingestion_status"], 0) + 1
        payload_items.append(payload)

    return {
        "scope": scope,
        "item_count": len(payload_items),
        "counts_by_document_type": type_counts,
        "counts_by_ingestion_status": status_counts,
        "active_job": _job_payload(active_job) if active_job else None,
        "items": payload_items,
    }


@router.post("/ingestion/jobs")
def create_ingestion_job(request: Request, payload: IngestionRequest) -> dict[str, Any]:
    container = request.app.state.container
    scope = resolve_scope(rfp_id=payload.rfp_id, submission_id=payload.submission_id)
    if (payload.rfp_id or payload.submission_id) and scope is None:
        raise HTTPException(status_code=404, detail="Requested RFP/submission scope was not found")
    master_metadata = _master_metadata_for_request(payload)

    try:
        job = container.ingestion_service.submit_job(
            limit=payload.limit,
            document_types=payload.document_types,
            source_files=payload.source_files,
            master_metadata=master_metadata,
            rfp_id=scope["rfp_id"] if scope else payload.rfp_id,
            submission_id=scope["submission_id"] if scope else payload.submission_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "scope": scope,
        "job": _job_payload(job),
    }


@router.get("/ingestion/jobs/{job_id}")
def get_ingestion_job(request: Request, job_id: str) -> dict[str, Any]:
    container = request.app.state.container
    job = container.ingestion_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return {"job": _job_payload(job)}


def _master_metadata_for_request(payload: IngestionRequest) -> MasterRFPMetadata | None:
    if not any([payload.issuing_authority, payload.customer, payload.rfp_id, payload.rfp_title]):
        return None
    return MasterRFPMetadata(
        issuing_authority=payload.issuing_authority,
        customer=payload.customer,
        rfp_id=payload.rfp_id,
        rfp_title=payload.rfp_title,
    )


def _summary_payload(summary: Any, *, master_metadata: MasterRFPMetadata | None) -> dict[str, Any]:
    return {
        "document_count": summary.document_count,
        "chunk_count": summary.chunk_count,
        "indexing": {
            "total_chunks": summary.indexing.total_chunks,
            "collections": [
                {
                    "document_type": item.document_type,
                    "collection_name": item.collection_name,
                    "chunk_count": item.chunk_count,
                }
                for item in summary.indexing.collections
            ],
        },
        "documents": [
            {
                "source_file": item.source_file.as_posix(),
                "document_type": item.document_type,
                "section_count": item.section_count,
                "chunk_count": item.chunk_count,
            }
            for item in summary.documents
        ],
        "master_metadata": {
            "issuing_authority": master_metadata.issuing_authority if master_metadata else None,
            "customer": master_metadata.customer if master_metadata else None,
            "rfp_id": master_metadata.rfp_id if master_metadata else None,
            "rfp_title": master_metadata.rfp_title if master_metadata else None,
        },
    }


def _scope_kwargs(scope: dict[str, Any] | None) -> dict[str, Any]:
    if not scope:
        return {"rfp_id": None, "submission_id": None}
    return {
        "rfp_id": scope.get("rfp_id"),
        "submission_id": scope.get("submission_id"),
    }


def _source_status_payload(item: Any, *, active_job: Any | None = None) -> dict[str, Any]:
    ingestion_status = item.ingestion_status
    if active_job and active_job.status not in TERMINAL_JOB_STATUSES:
        if item.source_file.as_posix() in set(active_job.source_files):
            if item.source_file.as_posix() in {document.source_file.as_posix() for document in active_job.documents}:
                ingestion_status = "ingested"
            elif active_job.status == "queued":
                ingestion_status = "queued"
            else:
                ingestion_status = "ingesting"
    return {
        "source_file": item.source_file.as_posix(),
        "document_type": item.document_type,
        "file_type": item.file_type,
        "support_status": item.support_status,
        "ingestion_status": ingestion_status,
        "chunk_count": item.chunk_count,
        "collection_name": getattr(item, "collection_name", None),
        "blob_etag": getattr(item, "blob_etag", None),
        "blob_last_modified": item.blob_last_modified.isoformat() if getattr(item, "blob_last_modified", None) else None,
        "indexed_blob_etag": getattr(item, "indexed_blob_etag", None),
        "indexed_blob_last_modified": getattr(item, "indexed_blob_last_modified", None),
        "indexed_ingested_at": getattr(item, "indexed_ingested_at", None),
    }


def _job_payload(job: Any) -> dict[str, Any]:
    progress_percent = 0
    if job.total_documents:
        progress_percent = int((job.processed_documents / job.total_documents) * 100)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "current_phase": job.current_phase,
        "rfp_id": job.rfp_id,
        "submission_id": job.submission_id,
        "document_types": list(job.document_types),
        "source_files": list(job.source_files),
        "limit": job.limit,
        "total_documents": job.total_documents,
        "processed_documents": job.processed_documents,
        "total_chunks": job.total_chunks,
        "progress_percent": progress_percent,
        "is_terminal": job.status in TERMINAL_JOB_STATUSES,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "indexing": {
            "total_chunks": job.indexing.total_chunks,
            "collections": [
                {
                    "document_type": item.document_type,
                    "collection_name": item.collection_name,
                    "chunk_count": item.chunk_count,
                }
                for item in job.indexing.collections
            ],
        },
        "documents": [
            {
                "source_file": item.source_file.as_posix(),
                "document_type": item.document_type,
                "section_count": item.section_count,
                "chunk_count": item.chunk_count,
            }
            for item in job.documents
        ],
        "errors": list(job.errors),
    }
