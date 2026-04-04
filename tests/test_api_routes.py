from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from rfp_rag_assistant.api.app import create_api_app
from rfp_rag_assistant.embeddings.chroma_indexer import IndexedCollectionResult, IndexingSummary
from rfp_rag_assistant.services.ingestion_service import IngestedDocumentResult, IngestionSummary


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

    def ingest_blob_documents(self, *, limit=None, document_types=None) -> IngestionSummary:
        self.calls.append({"limit": limit, "document_types": document_types})
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


def _build_test_client(monkeypatch) -> tuple[TestClient, _StubIngestionService]:
    ingestion = _StubIngestionService()
    app_runtime = SimpleNamespace(
        settings=SimpleNamespace(),
        container=SimpleNamespace(
            health_service=_StubHealthService(),
            blob_document_loader=_StubBlobDocumentLoader(),
            ingestion_service=ingestion,
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


def test_documents_route_lists_blob_documents(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)

    response = client.get("/documents")

    assert response.status_code == 200
    payload = response.json()
    assert payload["document_count"] == 3
    assert payload["counts_by_document_type"]["combined_qa"] == 1
    assert payload["counts_by_document_type"]["response_supporting_material"] == 1
    assert payload["documents"][0]["source_file"] == "combined_qa/ITT01.docx"


def test_reference_urls_route_lists_inventory(monkeypatch) -> None:
    client, _ = _build_test_client(monkeypatch)
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
    assert ingestion.calls == [{"limit": 5, "document_types": ["combined_qa"]}]
    assert ingestion.master_metadata is not None
    assert ingestion.master_metadata.issuing_authority == "Sussex Community NHS Foundation Trust"
