from __future__ import annotations

from types import SimpleNamespace

from rfp_rag_assistant.app import cli
from rfp_rag_assistant.embeddings.chroma_indexer import IndexedCollectionResult, IndexingSummary
from rfp_rag_assistant.services.ingestion_service import IngestedDocumentResult, IngestionSummary


class _StubIngestionService:
    def __init__(self) -> None:
        self.master_metadata = None
        self.calls: list[int | None] = []

    def ingest_blob_documents(self, *, limit: int | None = None) -> IngestionSummary:
        self.calls.append(limit)
        return IngestionSummary(
            document_count=2,
            chunk_count=5,
            indexing=IndexingSummary(
                total_chunks=5,
                collections=(
                    IndexedCollectionResult(
                        document_type="combined_qa",
                        collection_name="test_rfp_combined_qa",
                        chunk_count=3,
                    ),
                    IndexedCollectionResult(
                        document_type="response_supporting_material",
                        collection_name="test_rfp_response_supporting_material",
                        chunk_count=2,
                    ),
                ),
            ),
            documents=(
                IngestedDocumentResult(
                    source_file=__import__("pathlib").Path("combined_qa/ITT01.docx"),
                    document_type="combined_qa",
                    section_count=1,
                    chunk_count=3,
                ),
                IngestedDocumentResult(
                    source_file=__import__("pathlib").Path("response_supporting_material/mobilisation.xlsx"),
                    document_type="response_supporting_material",
                    section_count=12,
                    chunk_count=2,
                ),
            ),
        )


class _StubBlobService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def upload_file_to_blob(
        self,
        container_name,
        local_path,
        *,
        blob_name=None,
        relative_to=None,
        overwrite=False,
        metadata=None,
        content_type=None,
    ):
        resolved = blob_name or local_path.relative_to(relative_to).as_posix()
        self.calls.append(
            {
                "container_name": container_name,
                "local_path": local_path,
                "relative_to": relative_to,
                "overwrite": overwrite,
                "blob_name": resolved,
            }
        )
        return resolved


def test_cli_ingestion_command_prints_summary_and_sets_master_metadata(monkeypatch, capsys) -> None:
    stub_ingestion = _StubIngestionService()
    app = SimpleNamespace(
        settings=SimpleNamespace(),
        container=SimpleNamespace(ingestion_service=stub_ingestion),
    )

    monkeypatch.setattr(cli, "build_application", lambda: app)
    monkeypatch.setattr(
        cli,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                print_config=False,
                source_file=None,
                preview_background_file=None,
                preview_supporting_material_file=None,
                preview_tender_details_file=None,
                ingest_blob_documents=True,
                upload_local_folder=None,
                overwrite=False,
                limit=10,
                issuing_authority="Sussex Community NHS Foundation Trust",
                customer="Sussex Community NHS Foundation Trust",
                rfp_id="scft-wheelchair-2026",
                rfp_title="Wheelchair and Specialist Seating Service",
            )
        ),
    )

    cli.main()

    output = capsys.readouterr().out
    assert '"document_count": 2' in output
    assert '"collection_name": "test_rfp_combined_qa"' in output
    assert '"issuing_authority": "Sussex Community NHS Foundation Trust"' in output
    assert stub_ingestion.calls == [10]
    assert stub_ingestion.master_metadata is not None
    assert stub_ingestion.master_metadata.rfp_id == "scft-wheelchair-2026"


def test_cli_upload_command_preserves_relative_paths(monkeypatch, capsys, tmp_path) -> None:
    source_root = tmp_path / "RFP"
    combined = source_root / "combined_qa"
    supporting = source_root / "response_supporting_material"
    combined.mkdir(parents=True)
    supporting.mkdir(parents=True)
    (combined / "ITT01.docx").write_bytes(b"docx")
    (supporting / "plan.xlsx").write_bytes(b"xlsx")

    stub_blob = _StubBlobService()
    app = SimpleNamespace(
        settings=SimpleNamespace(azure_storage=SimpleNamespace(container="rfp-rag-assistant")),
        container=SimpleNamespace(blob_service=stub_blob),
    )

    monkeypatch.setattr(cli, "build_application", lambda: app)
    monkeypatch.setattr(
        cli,
        "build_parser",
        lambda: SimpleNamespace(
            parse_args=lambda: SimpleNamespace(
                print_config=False,
                source_file=None,
                preview_background_file=None,
                preview_supporting_material_file=None,
                preview_tender_details_file=None,
                ingest_blob_documents=False,
                upload_local_folder=source_root,
                overwrite=True,
                limit=None,
                issuing_authority=None,
                customer=None,
                rfp_id=None,
                rfp_title=None,
            )
        ),
    )

    cli.main()

    output = capsys.readouterr().out
    assert '"uploaded_count": 2' in output
    assert '"blob_name": "combined_qa/ITT01.docx"' in output
    assert '"blob_name": "response_supporting_material/plan.xlsx"' in output
    assert stub_blob.calls[0]["container_name"] == "rfp-rag-assistant"
    assert stub_blob.calls[0]["relative_to"] == source_root
