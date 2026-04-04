from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.embeddings.chroma_indexer import IndexingSummary
from rfp_rag_assistant.loaders.base import LoadedDocument
from rfp_rag_assistant.models import Chunk, ChunkMetadata, MasterRFPMetadata, ParsedDocument, ParsedSection
from rfp_rag_assistant.services.ingestion_service import IngestionService


@dataclass
class _StubBlobLoader:
    documents: list[Path]
    loaded: dict[Path, LoadedDocument]

    def list_documents(self) -> list[Path]:
        return list(self.documents)

    def load(self, source_file: Path) -> LoadedDocument:
        return self.loaded[source_file]


class _StubParser:
    def __init__(self) -> None:
        self.seen_payloads: list[Path] = []

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        payload = document.payload
        assert isinstance(payload, Path)
        self.seen_payloads.append(payload)
        return ParsedDocument(
            source_file=document.source_file,
            file_type=document.file_type,
            document_type="combined_qa",
            extracted_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            sections=[
                ParsedSection(
                    section_id="qa-1",
                    title="Clinical Governance",
                    text="Answer text",
                    kind="qa_pair",
                    structured_data={
                        "question_id": "ITT01",
                        "question_title": "Clinical Governance",
                        "question_text": "Describe your clinical governance approach.",
                        "answer_text": "Answer text",
                    },
                )
            ],
        )


class _StubChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        return [
            Chunk(
                chunk_id="qa-1-chunk-1",
                text="Question metadata: ITT01 | Clinical Governance\n\nAnswer: Answer text",
                embedding_text="Question metadata: ITT01 | Clinical Governance\n\nAnswer: Answer text",
                metadata=ChunkMetadata(
                    source_file=document.source_file,
                    file_type=document.file_type,
                    document_type=document.document_type,
                    chunk_type="qa_pair",
                    extra={
                        "section_title": "Clinical Governance",
                        "question_id": "ITT01",
                        "question_title": "Clinical Governance",
                        "question_text": "Describe your clinical governance approach.",
                    },
                ),
                structured_content={
                    "section_title": "Clinical Governance",
                    "question_id": "ITT01",
                    "question_title": "Clinical Governance",
                    "question_text": "Describe your clinical governance approach.",
                },
            )
        ]


class _StubIndexer:
    def __init__(self) -> None:
        self.seen_chunks: list[list[Chunk]] = []

    def upsert_chunks(self, chunks: list[Chunk]) -> IndexingSummary:
        self.seen_chunks.append(list(chunks))
        return IndexingSummary(total_chunks=len(chunks), collections=())


def test_ingestion_service_stages_blob_payload_and_indexes_chunks() -> None:
    source_file = Path("combined_qa/ITT01-Clinical Governance-Blatchford.docx")
    loader = _StubBlobLoader(
        documents=[source_file],
        loaded={
            source_file: LoadedDocument(
                source_file=source_file,
                file_type="docx",
                payload=b"fake-docx-bytes",
                metadata={"blob_name": source_file.as_posix()},
            )
        },
    )
    parser = _StubParser()
    chunker = _StubChunker()
    indexer = _StubIndexer()
    service = IngestionService(
        blob_document_loader=loader,
        parsers={"combined_qa": parser},
        chunkers={"combined_qa": chunker},
        chroma_indexer=indexer,
    )

    summary = service.ingest_blob_documents()

    assert summary.document_count == 1
    assert summary.chunk_count == 1
    assert summary.documents[0].document_type == "combined_qa"
    assert parser.seen_payloads[0].name == "ITT01-Clinical Governance-Blatchford.docx"
    assert parser.seen_payloads[0].read_bytes() == b"fake-docx-bytes"
    assert len(indexer.seen_chunks) == 1
    assert indexer.seen_chunks[0][0].metadata.document_type == "combined_qa"


def test_ingestion_service_applies_master_rfp_metadata_to_chunks() -> None:
    source_file = Path("combined_qa/ITT01-Clinical Governance-Blatchford.docx")
    loader = _StubBlobLoader(
        documents=[source_file],
        loaded={
            source_file: LoadedDocument(
                source_file=source_file,
                file_type="docx",
                payload=b"fake-docx-bytes",
                metadata={"blob_name": source_file.as_posix()},
            )
        },
    )
    indexer = _StubIndexer()
    service = IngestionService(
        blob_document_loader=loader,
        parsers={"combined_qa": _StubParser()},
        chunkers={"combined_qa": _StubChunker()},
        chroma_indexer=indexer,
        master_metadata=MasterRFPMetadata(
            issuing_authority="Sussex Community NHS Foundation Trust",
            customer="Sussex Community NHS Foundation Trust",
            rfp_id="scft-wheelchair-2026",
            rfp_title="Wheelchair and Specialist Seating Service",
        ),
    )

    service.ingest_blob_documents()

    chunk = indexer.seen_chunks[0][0]
    assert chunk.metadata.issuing_authority == "Sussex Community NHS Foundation Trust"
    assert chunk.metadata.customer == "Sussex Community NHS Foundation Trust"
    assert chunk.metadata.rfp_id == "scft-wheelchair-2026"
    assert chunk.metadata.rfp_title == "Wheelchair and Specialist Seating Service"
    assert chunk.structured_content["issuing_authority"] == "Sussex Community NHS Foundation Trust"


def test_ingestion_service_rejects_unknown_blob_prefix() -> None:
    source_file = Path("unknown_type/file.docx")
    loader = _StubBlobLoader(
        documents=[],
        loaded={},
    )
    service = IngestionService(
        blob_document_loader=loader,
        parsers={"combined_qa": _StubParser()},
        chunkers={"combined_qa": _StubChunker()},
        chroma_indexer=_StubIndexer(),
    )

    try:
        service._document_type_for_path(source_file)
    except ValueError as exc:
        assert "Unsupported document_type" in str(exc)
    else:
        raise AssertionError("Expected unknown blob prefix to be rejected")


def test_ingestion_service_maps_extracted_embedded_to_real_document_type() -> None:
    source_file = Path("extracted_embedded/background_requirements/ParentDoc/attachment.docx")
    loader = _StubBlobLoader(documents=[], loaded={})
    service = IngestionService(
        blob_document_loader=loader,
        parsers={"background_requirements": _StubParser()},
        chunkers={"background_requirements": _StubChunker()},
        chroma_indexer=_StubIndexer(),
    )

    assert service._document_type_for_path(source_file) == "background_requirements"
