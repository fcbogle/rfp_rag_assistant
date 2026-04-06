from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from rfp_rag_assistant.services.reconciliation_service import ReconciliationService


@dataclass
class _StubBlobDocumentLoader:
    container_name: str = "rfp-rag-assistant"

    def list_documents(self) -> list[Path]:
        return [
            Path("combined_qa/ITT01.docx"),
            Path("response_supporting_material/plan.xlsx"),
            Path("background_requirements/specification.pdf"),
        ]


class _StubBlobService:
    def get_blob_properties(self, container_name: str, blob_name: str) -> dict[str, object]:
        return {
            "combined_qa/ITT01.docx": {
                "etag": "etag-1",
                "last_modified": datetime(2026, 4, 6, 9, 0, tzinfo=UTC),
                "content_length": 1000,
            },
            "response_supporting_material/plan.xlsx": {
                "etag": "etag-2",
                "last_modified": datetime(2026, 4, 6, 9, 5, tzinfo=UTC),
                "content_length": 2000,
            },
            "background_requirements/specification.pdf": {
                "etag": "etag-3-new",
                "last_modified": datetime(2026, 4, 6, 9, 10, tzinfo=UTC),
                "content_length": 3000,
            },
        }[blob_name]


class _StubChromaIndexer:
    def list_indexed_sources(self, *, document_types=None):
        return {
            "response_supporting_material/plan.xlsx": {
                "source_file": "response_supporting_material/plan.xlsx",
                "document_type": "response_supporting_material",
                "collection_name": "test_rfp_response_supporting_material",
                "chunk_count": 4,
                "blob_etag": "etag-2",
                "blob_last_modified": "2026-04-06T09:05:00+00:00",
                "ingested_at": "2026-04-06T09:20:00+00:00",
            },
            "background_requirements/specification.pdf": {
                "source_file": "background_requirements/specification.pdf",
                "document_type": "background_requirements",
                "collection_name": "test_rfp_background_requirements",
                "chunk_count": 3,
                "blob_etag": "etag-3-old",
                "blob_last_modified": "2026-04-05T09:10:00+00:00",
                "ingested_at": "2026-04-05T09:20:00+00:00",
            },
        }


def test_reconciliation_service_derives_not_ingested_ingested_and_stale() -> None:
    service = ReconciliationService(
        blob_document_loader=_StubBlobDocumentLoader(),
        blob_service=_StubBlobService(),
        chroma_indexer=_StubChromaIndexer(),
    )

    items = service.list_source_status()

    by_file = {item.source_file.as_posix(): item for item in items}
    assert by_file["combined_qa/ITT01.docx"].ingestion_status == "not_ingested"
    assert by_file["response_supporting_material/plan.xlsx"].ingestion_status == "ingested"
    assert by_file["response_supporting_material/plan.xlsx"].chunk_count == 4
    assert by_file["background_requirements/specification.pdf"].ingestion_status == "stale"
