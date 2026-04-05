from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from rfp_rag_assistant.corpus_info import build_corpus_info
from rfp_rag_assistant.models import MasterRFPMetadata
from rfp_rag_assistant.reference_urls import load_reference_url_inventory
from rfp_rag_assistant.rfp_scopes import list_rfp_scopes, resolve_scope
from rfp_rag_assistant.source_paths import infer_document_type_from_path

router = APIRouter()


class IngestionRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1)
    document_types: list[str] | None = None
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
    try:
        documents = container.blob_document_loader.list_documents()
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    items = [
        {
            "source_file": document.as_posix(),
            "document_type": _document_type_for_path(document),
            "file_type": document.suffix.lstrip(".").lower(),
            "support_status": _support_status_for_path(document),
            "ingestion_status": "not_tracked",
        }
        for document in documents
    ]
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
    master_metadata = None
    if any([payload.issuing_authority, payload.customer, payload.rfp_id, payload.rfp_title]):
        master_metadata = MasterRFPMetadata(
            issuing_authority=payload.issuing_authority,
            customer=payload.customer,
            rfp_id=payload.rfp_id,
            rfp_title=payload.rfp_title,
        )
    container.ingestion_service.master_metadata = master_metadata

    try:
        summary = container.ingestion_service.ingest_blob_documents(
            limit=payload.limit,
            document_types=payload.document_types,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - operational path
        raise HTTPException(status_code=500, detail=str(exc)) from exc

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


def _document_type_for_path(source_file: Path) -> str:
    try:
        return infer_document_type_from_path(source_file)
    except ValueError:
        return ""


def _support_status_for_path(source_file: Path) -> str:
    suffix = source_file.suffix.lower()
    if suffix in {".docx", ".xlsx", ".pdf"}:
        return "supported"
    if suffix == ".pptx":
        return "unsupported"
    return "unknown"
