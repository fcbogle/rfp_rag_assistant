from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from rfp_rag_assistant.api.app import create_api_app
from rfp_rag_assistant.embeddings.chroma_indexer import IndexedCollectionResult, IndexingSummary
from rfp_rag_assistant.services.ingestion_service import (
    IngestedDocumentResult,
    IngestionJob,
    IngestionSummary,
    SourceIngestionStatus,
)


class _StubHealthService:
    def check(self) -> dict[str, bool]:
        return {
            "config_loaded": True,
            "openai_configured": True,
            "blob_storage_configured": True,
            "vector_store_configured": True,
        }


class _StubBlobDocumentLoader:
    container_name = "rfp-rag-assistant"
    prefix = ""

    def list_documents(self) -> list[Path]:
        return [
            Path("combined_qa/ITT01.docx"),
            Path("response_supporting_material/plan.xlsx"),
            Path("background_requirements/specification.pdf"),
        ]


class _StubIngestionService:
    def __init__(self) -> None:
        self.master_metadata = None
        self.calls: list[dict[str, object]] = []
        self.job_calls: list[dict[str, object]] = []

    def ingest_blob_documents(
        self,
        *,
        limit=None,
        document_types=None,
        source_files=None,
        master_metadata=None,
        rfp_id=None,
        submission_id=None,
    ) -> IngestionSummary:
        self.calls.append(
            {
                "limit": limit,
                "document_types": document_types,
                "source_files": source_files,
                "rfp_id": rfp_id,
                "submission_id": submission_id,
                "master_metadata": master_metadata,
            }
        )
        return IngestionSummary(
            document_count=1,
            chunk_count=3,
            indexing=IndexingSummary(
                total_chunks=3,
                collections=(
                    IndexedCollectionResult(
                        document_type="combined_qa",
                        collection_name="test_rfp_combined_qa",
                        chunk_count=3,
                    ),
                ),
            ),
            documents=(
                IngestedDocumentResult(
                    source_file=Path("combined_qa/ITT01.docx"),
                    document_type="combined_qa",
                    section_count=1,
                    chunk_count=3,
                ),
            ),
        )

    def list_source_status(self, *, rfp_id=None, submission_id=None, document_types=None):
        return ()

    def get_active_job(self, *, rfp_id=None, submission_id=None):
        return IngestionJob(
            job_id="job-123",
            status="running",
            current_phase="processing 1 of 2",
            rfp_id=rfp_id,
            submission_id=submission_id,
            document_types=("combined_qa",),
            source_files=("combined_qa/ITT01.docx",),
            limit=5,
            total_documents=2,
            processed_documents=1,
            total_chunks=3,
            indexing=IndexingSummary(total_chunks=0, collections=()),
            documents=(),
            errors=(),
            created_at=datetime(2026, 4, 5, 9, 50, tzinfo=UTC),
            started_at=datetime(2026, 4, 5, 9, 51, tzinfo=UTC),
        )

    def submit_job(
        self,
        *,
        limit=None,
        document_types=None,
        source_files=None,
        master_metadata=None,
        rfp_id=None,
        submission_id=None,
    ):
        self.job_calls.append(
            {
                "limit": limit,
                "document_types": document_types,
                "source_files": source_files,
                "rfp_id": rfp_id,
                "submission_id": submission_id,
                "master_metadata": master_metadata,
            }
        )
        return IngestionJob(
            job_id="job-999",
            status="queued",
            current_phase="queued",
            rfp_id=rfp_id,
            submission_id=submission_id,
            document_types=tuple(document_types or ()),
            source_files=tuple(source_files or ()),
            limit=limit,
            total_documents=3,
            processed_documents=0,
            total_chunks=0,
            indexing=IndexingSummary(total_chunks=0, collections=()),
            documents=(),
            errors=(),
            created_at=datetime(2026, 4, 5, 11, 0, tzinfo=UTC),
        )

    def get_job(self, job_id):
        if job_id != "job-999":
            return None
        return IngestionJob(
            job_id="job-999",
            status="completed",
            current_phase="completed",
            rfp_id="scft-wheelchair-2026",
            submission_id="blatchford-primary-response",
            document_types=("combined_qa",),
            source_files=("combined_qa/ITT01.docx",),
            limit=5,
            total_documents=1,
            processed_documents=1,
            total_chunks=3,
            indexing=IndexingSummary(
                total_chunks=3,
                collections=(
                    IndexedCollectionResult(
                        document_type="combined_qa",
                        collection_name="test_rfp_combined_qa",
                        chunk_count=3,
                    ),
                ),
            ),
            documents=(
                IngestedDocumentResult(
                    source_file=Path("combined_qa/ITT01.docx"),
                    document_type="combined_qa",
                    section_count=1,
                    chunk_count=3,
                ),
            ),
            errors=(),
            created_at=datetime(2026, 4, 5, 11, 0, tzinfo=UTC),
            started_at=datetime(2026, 4, 5, 11, 0, 10, tzinfo=UTC),
            completed_at=datetime(2026, 4, 5, 11, 0, 30, tzinfo=UTC),
        )


def _build_test_client(monkeypatch) -> tuple[TestClient, _StubIngestionService]:
    reconciliation_items = (
        SimpleNamespace(
            source_file=Path("combined_qa/ITT01.docx"),
            document_type="combined_qa",
            file_type="docx",
            support_status="supported",
            ingestion_status="not_ingested",
            chunk_count=0,
            collection_name=None,
            blob_etag="etag-a",
            blob_last_modified=datetime(2026, 4, 5, 8, 0, tzinfo=UTC),
            indexed_blob_etag=None,
            indexed_blob_last_modified=None,
            indexed_ingested_at=None,
        ),
        SimpleNamespace(
            source_file=Path("response_supporting_material/plan.xlsx"),
            document_type="response_supporting_material",
            file_type="xlsx",
            support_status="supported",
            ingestion_status="ingested",
            chunk_count=4,
            collection_name="test_rfp_response_supporting_material",
            blob_etag="etag-b",
            blob_last_modified=datetime(2026, 4, 5, 8, 30, tzinfo=UTC),
            indexed_blob_etag="etag-b",
            indexed_blob_last_modified="2026-04-05T08:30:00+00:00",
            indexed_ingested_at="2026-04-05T08:45:00+00:00",
        ),
        SimpleNamespace(
            source_file=Path("background_requirements/specification.pdf"),
            document_type="background_requirements",
            file_type="pdf",
            support_status="supported",
            ingestion_status="stale",
            chunk_count=2,
            collection_name="test_rfp_background_requirements",
            blob_etag="etag-c-new",
            blob_last_modified=datetime(2026, 4, 5, 9, 0, tzinfo=UTC),
            indexed_blob_etag="etag-c-old",
            indexed_blob_last_modified="2026-04-04T09:00:00+00:00",
            indexed_ingested_at="2026-04-04T09:30:00+00:00",
        ),
    )
    ingestion = _StubIngestionService()
    reconciliation = SimpleNamespace(
        list_source_status=lambda **_: reconciliation_items,
        build_snapshot=lambda **_: SimpleNamespace(
            items=reconciliation_items,
            blob_file_count=3,
            indexed_source_count=2,
            collections_scanned=("test_rfp_background_requirements", "test_rfp_response_supporting_material"),
        )
    )
    app_runtime = SimpleNamespace(
        settings=SimpleNamespace(),
        container=SimpleNamespace(
            health_service=_StubHealthService(),
            blob_document_loader=_StubBlobDocumentLoader(),
            ingestion_service=ingestion,
            reconciliation_service=reconciliation,
            chroma_indexer=SimpleNamespace(),
        ),
    )
    monkeypatch.setattr("rfp_rag_assistant.api.app.build_application", lambda **_: app_runtime)
    app = create_api_app()
    return TestClient(app), ingestion


def test_health_route(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["config_loaded"] is True


def test_rfp_scopes_route_lists_available_scopes(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.list_rfp_scopes",
        lambda: [
            {
                "rfp_id": "scft-wheelchair-2026",
                "submission_id": "blatchford-primary-response",
                "rfp_title": "Wheelchair and Specialist Seating Service",
                "submission_title": "Blatchford Primary Response Set",
                "issuing_authority": "Sussex Community NHS Foundation Trust",
                "response_owner": "Blatchford",
            }
        ],
    )

    response = client.get("/rfp-scopes")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope_count"] == 1
    assert payload["scopes"][0]["rfp_id"] == "scft-wheelchair-2026"


def test_documents_route_lists_blob_documents(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.resolve_scope",
        lambda **_: {"rfp_id": "scft-wheelchair-2026", "submission_id": "blatchford-primary-response"},
    )

    response = client.get("/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["rfp_id"] == "scft-wheelchair-2026"
    assert payload["document_count"] == 3
    assert payload["counts_by_document_type"]["combined_qa"] == 1
    assert payload["counts_by_document_type"]["response_supporting_material"] == 1
    assert payload["documents"][0]["source_file"] == "combined_qa/ITT01.docx"
    assert payload["documents"][0]["support_status"] == "supported"
    assert payload["documents"][0]["ingestion_status"] == "not_ingested"


def test_corpus_info_route_returns_storage_and_classification_metadata(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.resolve_scope",
        lambda **_: {"rfp_id": "scft-wheelchair-2026", "submission_id": "blatchford-primary-response"},
    )
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.build_corpus_info",
        lambda settings, chroma_indexer: {
            "blob": {
                "account": "blob-account",
                "container": "rfp-rag-assistant",
                "prefix": "",
                "region": "uksouth",
                "supported_extensions": [".docx", ".xlsx", ".pdf"],
            },
            "chroma": {
                "endpoint": "https://api.trychroma.com",
                "database": "RFP",
                "tenant": "tenant",
                "region": "eu-west-2",
                "namespace": "test_rfp",
                "collection_base": "rfp_answers",
                "target_collections": [{"document_type": "combined_qa", "collection_name": "test_rfp_combined_qa"}],
            },
            "classifications": [{"document_type": "combined_qa", "title": "Combined Q&A"}],
        },
    )

    response = client.get("/corpus-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["rfp_id"] == "scft-wheelchair-2026"
    assert payload["blob"]["container"] == "rfp-rag-assistant"
    assert payload["blob"]["region"] == "uksouth"
    assert payload["chroma"]["region"] == "eu-west-2"
    assert payload["chroma"]["namespace"] == "test_rfp"
    assert payload["classifications"][0]["document_type"] == "combined_qa"


def test_reference_urls_route_lists_inventory(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.resolve_scope",
        lambda **_: {"rfp_id": "scft-wheelchair-2026", "submission_id": "blatchford-primary-response"},
    )
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.load_reference_url_inventory",
        lambda: [
            {
                "document_type": "background_requirements",
                "status": "ingest",
                "reference_origin": "customer_cited",
                "source_format": "docx_or_xlsx",
                "url": "https://example.com/a",
            },
            {
                "document_type": "combined_qa",
                "status": "review",
                "reference_origin": "supplier_cited",
                "source_format": "docx_or_xlsx",
                "url": "https://example.com/b",
            },
        ],
    )

    response = client.get("/reference-urls")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scope"]["rfp_id"] == "scft-wheelchair-2026"
    assert payload["reference_url_count"] == 2
    assert payload["counts_by_document_type"]["background_requirements"] == 1
    assert payload["counts_by_status"]["ingest"] == 1
    assert payload["items"][0]["url"] == "https://example.com/a"


def test_ingestion_route_triggers_ingestion_with_metadata(monkeypatch) -> None:
    client, ingestion = _build_test_client(monkeypatch)

    response = client.post(
        "/ingestion",
        json={
            "limit": 5,
            "document_types": ["combined_qa"],
            "issuing_authority": "Sussex Community NHS Foundation Trust",
            "customer": "Sussex Community NHS Foundation Trust",
            "rfp_id": "scft-wheelchair-2026",
            "rfp_title": "Wheelchair and Specialist Seating Service",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_count"] == 1
    assert payload["indexing"]["collections"][0]["collection_name"] == "test_rfp_combined_qa"
    assert ingestion.calls[0]["limit"] == 5
    assert ingestion.calls[0]["document_types"] == ["combined_qa"]
    assert ingestion.calls[0]["rfp_id"] == "scft-wheelchair-2026"
    assert ingestion.master_metadata is not None
    assert ingestion.master_metadata.issuing_authority == "Sussex Community NHS Foundation Trust"


def test_source_status_route_lists_per_file_status_and_active_job(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.resolve_scope",
        lambda **_: {"rfp_id": "scft-wheelchair-2026", "submission_id": "blatchford-primary-response"},
    )

    response = client.get("/ingestion/source-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["item_count"] == 3
    assert payload["blob_file_count"] == 3
    assert payload["indexed_source_count"] == 2
    assert "test_rfp_background_requirements" in payload["collections_scanned"]
    assert payload["counts_by_ingestion_status"]["ingesting"] == 1
    assert payload["active_job"]["job_id"] == "job-123"
    assert payload["items"][1]["chunk_count"] == 4


def test_create_ingestion_job_returns_job_payload(monkeypatch) -> None:
    client, ingestion = _build_test_client(monkeypatch)
    monkeypatch.setattr(
        "rfp_rag_assistant.api.routes.resolve_scope",
        lambda **_: {"rfp_id": "scft-wheelchair-2026", "submission_id": "blatchford-primary-response"},
    )

    response = client.post(
        "/ingestion/jobs",
        json={
            "limit": 5,
            "document_types": ["combined_qa"],
            "rfp_id": "scft-wheelchair-2026",
            "submission_id": "blatchford-primary-response",
            "issuing_authority": "Sussex Community NHS Foundation Trust",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["job_id"] == "job-999"
    assert payload["job"]["status"] == "queued"
    assert ingestion.job_calls[0]["rfp_id"] == "scft-wheelchair-2026"
    assert ingestion.job_calls[0]["submission_id"] == "blatchford-primary-response"


def test_get_ingestion_job_returns_job_snapshot(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)

    response = client.get("/ingestion/jobs/job-999")

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "completed"
    assert payload["job"]["documents"][0]["source_file"] == "combined_qa/ITT01.docx"
