from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from rfp_rag_assistant.config import ChromaSettings
from rfp_rag_assistant.embeddings import ChromaIndexer
from rfp_rag_assistant.models import Chunk, ChunkMetadata, SourceReference


@dataclass
class _FakeCollection:
    name: str
    upsert_calls: list[dict[str, object]] = field(default_factory=list)
    get_result: dict[str, object] = field(default_factory=lambda: {"metadatas": []})

    def upsert(
        self,
        *,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, object]],
        embeddings: list[list[float]],
    ) -> None:
        self.upsert_calls.append(
            {
                "ids": ids,
                "documents": documents,
                "metadatas": metadatas,
                "embeddings": embeddings,
            }
        )

    def get(self, *, include: list[str]) -> dict[str, object]:
        return self.get_result


@dataclass
class _FakeClient:
    collections: dict[str, _FakeCollection] = field(default_factory=dict)

    def get_or_create_collection(self, *, name: str) -> _FakeCollection:
        if name not in self.collections:
            self.collections[name] = _FakeCollection(name=name)
        return self.collections[name]


class _FakeEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        self.calls.append([chunk.chunk_id for chunk in chunks])
        return [[float(index), float(index + 1)] for index, _ in enumerate(chunks, start=1)]


class _MismatchEmbedder:
    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        return [[1.0, 0.0]]


def _combined_chunk() -> Chunk:
    return Chunk(
        chunk_id="qa-1",
        text="Question metadata: ITT01 | Clinical Governance\nAnswer text",
        embedding_text="Question metadata: ITT01 | Clinical Governance\nAnswer text",
        metadata=ChunkMetadata(
            source_file=Path("combined_qa/ITT01.docx"),
            file_type="docx",
            document_type="combined_qa",
            chunk_type="qa_pair",
            source_reference=SourceReference(
                source_file=Path("combined_qa/ITT01.docx"),
                file_type="docx",
                document_type="combined_qa",
                section_id="qa_pair:itt01",
            ),
            extra={
                "section_title": "Clinical Governance",
                "question_id": "ITT01",
                "question_title": "Clinical Governance",
                "question_text": "Describe your clinical governance approach.",
                "chunk_index": 1,
                "chunk_total": 1,
            },
        ),
        structured_content={
            "section_title": "Clinical Governance",
            "question_id": "ITT01",
            "question_title": "Clinical Governance",
            "question_text": "Describe your clinical governance approach.",
        },
    )


def _supporting_chunk() -> Chunk:
    return Chunk(
        chunk_id="support-1",
        text="Mobilisation team profile",
        embedding_text="Mobilisation team profile",
        metadata=ChunkMetadata(
            source_file=Path("response_supporting_material/mobilisation.xlsx"),
            file_type="xlsx",
            document_type="response_supporting_material",
            chunk_type="spreadsheet_row_group",
            sheet_name="1 Mobilisation Team",
            source_reference=SourceReference(
                source_file=Path("response_supporting_material/mobilisation.xlsx"),
                file_type="xlsx",
                document_type="response_supporting_material",
                sheet_name="1 Mobilisation Team",
                row_index=4,
                section_id="sheet:1 Mobilisation Team:row_group:4",
            ),
            extra={
                "section_title": "Beth Pitcairn",
                "row_index": 4,
                "chunk_index": 1,
                "chunk_total": 1,
            },
        ),
        structured_content={
            "section_title": "Beth Pitcairn",
            "sheet_name": "1 Mobilisation Team",
            "row_index": 4,
        },
    )


def test_chroma_indexer_routes_chunks_to_namespaced_collections() -> None:
    fake_client = _FakeClient()
    fake_embedder = _FakeEmbedder()
    indexer = ChromaIndexer(
        settings=ChromaSettings(namespace="test", collection="rfp_answers"),
        embedder=fake_embedder,
        client_factory=lambda _: fake_client,
    )

    summary = indexer.upsert_chunks([_combined_chunk(), _supporting_chunk()])

    assert summary.total_chunks == 2
    assert {result.collection_name for result in summary.collections} == {
        "test_combined_qa",
        "test_response_supporting_material",
    }
    assert fake_embedder.calls == [["qa-1"], ["support-1"]]

    combined_call = fake_client.collections["test_combined_qa"].upsert_calls[0]
    assert combined_call["ids"] == ["qa-1"]
    assert combined_call["documents"] == ["Question metadata: ITT01 | Clinical Governance\nAnswer text"]
    combined_metadata = combined_call["metadatas"][0]
    assert combined_metadata["question_id"] == "ITT01"
    assert combined_metadata["document_type"] == "combined_qa"

    supporting_call = fake_client.collections["test_response_supporting_material"].upsert_calls[0]
    supporting_metadata = supporting_call["metadatas"][0]
    assert supporting_metadata["sheet_name"] == "1 Mobilisation Team"
    assert supporting_metadata["row_index"] == 4


def test_chroma_indexer_uses_collection_prefix_when_configured() -> None:
    indexer = ChromaIndexer(
        settings=ChromaSettings(namespace="prod", collection="rfp_history"),
        embedder=_FakeEmbedder(),
        client_factory=lambda _: _FakeClient(),
    )

    assert indexer.collection_name_for("combined_qa") == "prod_rfp_history_combined_qa"


def test_chroma_indexer_rejects_embedding_count_mismatch() -> None:
    indexer = ChromaIndexer(
        settings=ChromaSettings(namespace="test", collection="rfp_answers"),
        embedder=_MismatchEmbedder(),
        client_factory=lambda _: _FakeClient(),
    )

    with pytest.raises(ValueError, match="Embedding count mismatch for response_supporting_material"):
        indexer.upsert_chunks([_supporting_chunk(), _supporting_chunk()])


def test_chroma_indexer_lists_indexed_sources_from_collection_metadata() -> None:
    combined_collection = _FakeCollection(
        name="test_combined_qa",
        get_result={
            "metadatas": [
                {
                    "source_file": "combined_qa/ITT01.docx",
                    "blob_etag": "etag-1",
                    "blob_last_modified": "2026-04-06T09:00:00+00:00",
                    "ingested_at": "2026-04-06T09:05:00+00:00",
                },
                {
                    "source_file": "combined_qa/ITT01.docx",
                    "blob_etag": "etag-1",
                    "blob_last_modified": "2026-04-06T09:00:00+00:00",
                    "ingested_at": "2026-04-06T09:05:00+00:00",
                },
            ]
        },
    )
    fake_client = _FakeClient(collections={"test_combined_qa": combined_collection})
    indexer = ChromaIndexer(
        settings=ChromaSettings(namespace="test", collection="rfp_answers"),
        embedder=_FakeEmbedder(),
        client_factory=lambda _: fake_client,
    )

    indexed = indexer.list_indexed_sources(document_types=["combined_qa"])

    assert indexed["combined_qa/ITT01.docx"]["chunk_count"] == 2
    assert indexed["combined_qa/ITT01.docx"]["blob_etag"] == "etag-1"
