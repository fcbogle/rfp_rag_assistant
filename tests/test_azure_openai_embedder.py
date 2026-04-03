from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.config import AzureOpenAISettings
from rfp_rag_assistant.embeddings import AzureOpenAIEmbedder
from rfp_rag_assistant.models import Chunk, ChunkMetadata


@dataclass
class _FakeEmbeddingItem:
    embedding: list[float]


@dataclass
class _FakeResponse:
    data: list[_FakeEmbeddingItem]


class _FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def create(self, *, model: str, input: list[str]) -> _FakeResponse:  # noqa: A002
        self.calls.append(list(input))
        base = {
            "connection test": [3.0, 4.0],
            "chunk a": [1.0, 0.0],
            "chunk b": [0.0, 2.0],
        }
        return _FakeResponse(data=[_FakeEmbeddingItem(embedding=base[text]) for text in input])


class _FakeClient:
    def __init__(self) -> None:
        self.embeddings = _FakeEmbeddingsAPI()


def _settings() -> AzureOpenAISettings:
    return AzureOpenAISettings(
        api_key="secret",
        endpoint="https://aoai-ifu-dev.openai.azure.com",
        api_version="2024-10-21",
        embed_deployment="emb-3-large",
    )


def test_azure_openai_embedder_reports_configuration() -> None:
    embedder = AzureOpenAIEmbedder(settings=_settings(), client_factory=lambda _: _FakeClient())

    assert embedder.is_configured() is True
    assert embedder.test_connection() is True
    assert embedder.embedding_dim == 2


def test_azure_openai_embedder_embeds_chunks_in_batches() -> None:
    fake_client = _FakeClient()
    embedder = AzureOpenAIEmbedder(
        settings=_settings(),
        batch_size=1,
        client_factory=lambda _: fake_client,
    )
    chunks = [
        Chunk(
            chunk_id="a",
            text="chunk a",
            embedding_text="chunk a",
            metadata=ChunkMetadata(
                source_file=Path("a.docx"),
                file_type="docx",
                document_type="combined_qa",
                chunk_type="qa_pair",
                extra={"section_title": "A", "question_id": "ITT01", "question_title": "A", "question_text": "Q"},
            ),
        ),
        Chunk(
            chunk_id="b",
            text="chunk b",
            embedding_text="chunk b",
            metadata=ChunkMetadata(
                source_file=Path("b.docx"),
                file_type="docx",
                document_type="combined_qa",
                chunk_type="qa_pair",
                extra={"section_title": "B", "question_id": "ITT02", "question_title": "B", "question_text": "Q"},
            ),
        ),
    ]

    vectors = embedder.embed(chunks)

    assert len(vectors) == 2
    assert fake_client.embeddings.calls == [["chunk a"], ["chunk b"]]
    assert vectors[0] == [1.0, 0.0]
    assert vectors[1] == [0.0, 1.0]


def test_azure_openai_embedder_requires_complete_settings() -> None:
    embedder = AzureOpenAIEmbedder(
        settings=AzureOpenAISettings(api_key="", endpoint="", embed_deployment=""),
        client_factory=lambda _: _FakeClient(),
    )

    assert embedder.is_configured() is False
    assert embedder.test_connection() is False
