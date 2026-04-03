from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from rfp_rag_assistant.models import Chunk

ScalarMetadata = str | int | float | bool


@dataclass(slots=True, frozen=True)
class ChromaRecord:
    record_id: str
    document: str
    metadata: dict[str, ScalarMetadata]


@dataclass(slots=True, frozen=True)
class MetadataSchemaSpec:
    document_type: str
    required_fields: tuple[str, ...]


COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "chunk_id",
    "source_file",
    "file_type",
    "document_type",
    "chunk_type",
    "section_title",
)


DOCUMENT_TYPE_SCHEMAS: dict[str, MetadataSchemaSpec] = {
    "combined_qa": MetadataSchemaSpec(
        document_type="combined_qa",
        required_fields=COMMON_REQUIRED_FIELDS + ("question_id", "question_title", "question_text"),
    ),
    "response_supporting_material": MetadataSchemaSpec(
        document_type="response_supporting_material",
        required_fields=COMMON_REQUIRED_FIELDS,
    ),
    "background_requirements": MetadataSchemaSpec(
        document_type="background_requirements",
        required_fields=COMMON_REQUIRED_FIELDS,
    ),
    "tender_details": MetadataSchemaSpec(
        document_type="tender_details",
        required_fields=COMMON_REQUIRED_FIELDS,
    ),
    "external_reference": MetadataSchemaSpec(
        document_type="external_reference",
        required_fields=COMMON_REQUIRED_FIELDS + ("source_url", "source_domain", "reference_origin"),
    ),
}


def chunk_to_chroma_record(chunk: Chunk) -> ChromaRecord:
    metadata = flatten_chunk_metadata(chunk)
    validate_chroma_metadata(metadata)
    return ChromaRecord(
        record_id=chunk.chunk_id,
        document=chunk.embedding_text,
        metadata=metadata,
    )


def flatten_chunk_metadata(chunk: Chunk) -> dict[str, ScalarMetadata]:
    metadata: dict[str, ScalarMetadata] = {
        "chunk_id": chunk.chunk_id,
        "source_file": _as_string(chunk.metadata.source_file),
        "file_type": chunk.metadata.file_type,
        "document_type": chunk.metadata.document_type,
        "chunk_type": chunk.metadata.chunk_type,
        "heading_path": " > ".join(chunk.metadata.heading_path),
        "section_title": _coalesce(
            chunk.metadata.extra.get("section_title"),
            chunk.structured_content.get("section_title"),
        ),
        "section_title_normalized": _coalesce(
            chunk.metadata.extra.get("section_title_normalized"),
            chunk.structured_content.get("section_title_normalized"),
        ),
        "sheet_name": _coalesce(
            chunk.metadata.sheet_name,
            chunk.structured_content.get("sheet_name"),
        ),
        "row_index": _as_scalar(_coalesce(chunk.metadata.extra.get("row_index"), chunk.structured_content.get("row_index"))),
        "chunk_index": _as_scalar(chunk.metadata.extra.get("chunk_index")),
        "chunk_total": _as_scalar(chunk.metadata.extra.get("chunk_total")),
        "customer": _as_scalar(chunk.metadata.customer),
        "date": _as_date_string(chunk.metadata.date),
        "product_or_service_area": _as_scalar(chunk.metadata.product_or_service_area),
        "region": _as_scalar(chunk.metadata.region),
        "approval_status": _as_scalar(chunk.metadata.approval_status),
        "reusable_flag": _as_scalar(chunk.metadata.reusable_flag),
        "source_reference_section_id": _as_scalar(
            chunk.metadata.source_reference.section_id if chunk.metadata.source_reference else None
        ),
        "source_reference_row_index": _as_scalar(
            chunk.metadata.source_reference.row_index if chunk.metadata.source_reference else None
        ),
        "source_reference_sheet_name": _as_scalar(
            chunk.metadata.source_reference.sheet_name if chunk.metadata.source_reference else None
        ),
        "question_id": _coalesce(
            chunk.metadata.extra.get("question_id"),
            chunk.structured_content.get("question_id"),
        ),
        "question_title": _coalesce(
            chunk.metadata.extra.get("question_title"),
            chunk.structured_content.get("question_title"),
        ),
        "question_text": _coalesce(
            chunk.metadata.extra.get("question_text"),
            chunk.structured_content.get("question_text"),
        ),
        "source_url": _coalesce(
            chunk.metadata.extra.get("source_url"),
            chunk.structured_content.get("source_url"),
        ),
        "source_domain": _coalesce(
            chunk.metadata.extra.get("source_domain"),
            chunk.structured_content.get("source_domain"),
        ),
        "reference_origin": _coalesce(
            chunk.metadata.extra.get("reference_origin"),
            chunk.structured_content.get("reference_origin"),
        ),
    }

    compact = {
        key: value
        for key, value in metadata.items()
        if value not in (None, "")
    }
    return compact


def validate_chroma_metadata(metadata: dict[str, ScalarMetadata]) -> None:
    document_type = str(metadata.get("document_type", "")).strip()
    if not document_type:
        raise ValueError("Missing required Chroma metadata field: document_type")

    spec = DOCUMENT_TYPE_SCHEMAS.get(document_type)
    if spec is None:
        raise ValueError(f"Unsupported document_type for Chroma schema: {document_type}")

    missing = [field for field in spec.required_fields if metadata.get(field) in (None, "")]
    if missing:
        raise ValueError(
            f"Missing required Chroma metadata fields for {document_type}: {', '.join(missing)}"
        )

    chunk_type = str(metadata.get("chunk_type", "")).strip()
    if document_type in {"response_supporting_material", "tender_details"} and chunk_type in {
        "spreadsheet_row",
        "spreadsheet_row_group",
    }:
        if metadata.get("sheet_name") in (None, ""):
            raise ValueError(f"Missing required Chroma metadata field for {document_type} spreadsheet chunk: sheet_name")


def _coalesce(*values: Any) -> ScalarMetadata | None:
    for value in values:
        scalar = _as_scalar(value)
        if scalar not in (None, ""):
            return scalar
    return None


def _as_scalar(value: Any) -> ScalarMetadata | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _as_string(value: Path | str) -> str:
    return str(value)


def _as_date_string(value: date | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
