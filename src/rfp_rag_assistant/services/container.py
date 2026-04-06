from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rfp_rag_assistant.config import AppSettings, load_config
from rfp_rag_assistant.chunkers import (
    BackgroundRequirementsChunker,
    ExternalReferenceChunker,
    ITTCombinedQAChunker,
    ResponseSupportingMaterialChunker,
    TenderDetailsChunker,
)
from rfp_rag_assistant.embeddings import AzureOpenAIEmbedder, ChromaIndexer
from rfp_rag_assistant.loaders.blob_document_loader import BlobDocumentLoader
from rfp_rag_assistant.models import RetrievalResult
from rfp_rag_assistant.parsers import (
    BackgroundRequirementsParser,
    CombinedQAParser,
    HTMLReferenceParser,
    ResponseSupportingMaterialParser,
    TenderDetailsParser,
)
from rfp_rag_assistant.retrieval import Retriever
from rfp_rag_assistant.services.blob_service import BlobService
from rfp_rag_assistant.services.draft_service import DraftService
from rfp_rag_assistant.services.health_service import HealthService
from rfp_rag_assistant.services.ingestion_service import IngestionService
from rfp_rag_assistant.services.query_service import QueryService
from rfp_rag_assistant.services.reconciliation_service import ReconciliationService


class NullRetriever:
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        return []


def build_blob_service(settings: AppSettings) -> BlobService:
    return BlobService(settings=settings)


def build_blob_document_loader(settings: AppSettings, blob_service: BlobService) -> BlobDocumentLoader:
    return BlobDocumentLoader(
        blob_service=blob_service,
        container_name=settings.azure_storage.container,
        prefix=settings.azure_storage.prefix,
        supported_extensions=settings.supported_extensions,
    )


def build_parsers() -> dict[str, object]:
    return {
        "combined_qa": CombinedQAParser(),
        "background_requirements": BackgroundRequirementsParser(),
        "response_supporting_material": ResponseSupportingMaterialParser(),
        "tender_details": TenderDetailsParser(),
        "external_reference": HTMLReferenceParser(),
    }


def build_chunkers(settings: AppSettings) -> dict[str, object]:
    return {
        "combined_qa": ITTCombinedQAChunker(
            chunk_size_tokens=settings.ingestion.chunk_size_tokens,
            overlap_tokens=settings.ingestion.overlap_tokens,
        ),
        "background_requirements": BackgroundRequirementsChunker(
            chunk_size_tokens=settings.ingestion.chunk_size_tokens,
            overlap_tokens=settings.ingestion.overlap_tokens,
        ),
        "response_supporting_material": ResponseSupportingMaterialChunker(
            chunk_size_tokens=settings.ingestion.chunk_size_tokens,
            overlap_tokens=settings.ingestion.overlap_tokens,
        ),
        "tender_details": TenderDetailsChunker(
            chunk_size_tokens=settings.ingestion.chunk_size_tokens,
            overlap_tokens=settings.ingestion.overlap_tokens,
        ),
        "external_reference": ExternalReferenceChunker(
            chunk_size_tokens=settings.ingestion.chunk_size_tokens,
            overlap_tokens=settings.ingestion.overlap_tokens,
        ),
    }


def build_embedder(settings: AppSettings) -> AzureOpenAIEmbedder:
    return AzureOpenAIEmbedder(settings=settings.azure_openai)


def build_chroma_indexer(settings: AppSettings, embedder: AzureOpenAIEmbedder) -> ChromaIndexer:
    return ChromaIndexer(settings=settings.chroma, embedder=embedder)


def build_ingestion_service(
    blob_document_loader: BlobDocumentLoader,
    parsers: dict[str, object],
    chunkers: dict[str, object],
    chroma_indexer: ChromaIndexer,
) -> IngestionService:
    return IngestionService(
        blob_document_loader=blob_document_loader,
        parsers=parsers,
        chunkers=chunkers,
        chroma_indexer=chroma_indexer,
    )


def build_reconciliation_service(
    blob_document_loader: BlobDocumentLoader,
    blob_service: BlobService,
    chroma_indexer: ChromaIndexer,
    settings: AppSettings,
) -> ReconciliationService:
    return ReconciliationService(
        blob_document_loader=blob_document_loader,
        blob_service=blob_service,
        chroma_indexer=chroma_indexer,
        supported_extensions=settings.supported_extensions,
    )


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    retriever: Retriever
    blob_service: BlobService = field(init=False)
    blob_document_loader: BlobDocumentLoader = field(init=False)
    parsers: dict[str, object] = field(init=False)
    chunkers: dict[str, object] = field(init=False)
    embedder: AzureOpenAIEmbedder = field(init=False)
    chroma_indexer: ChromaIndexer = field(init=False)
    ingestion_service: IngestionService = field(init=False)
    reconciliation_service: ReconciliationService = field(init=False)
    query_service: QueryService = field(init=False)
    draft_service: DraftService = field(init=False)
    health_service: HealthService = field(init=False)

    def __post_init__(self) -> None:
        self.blob_service = build_blob_service(settings=self.settings)
        self.blob_document_loader = build_blob_document_loader(
            settings=self.settings,
            blob_service=self.blob_service,
        )
        self.parsers = build_parsers()
        self.chunkers = build_chunkers(settings=self.settings)
        self.embedder = build_embedder(settings=self.settings)
        self.chroma_indexer = build_chroma_indexer(settings=self.settings, embedder=self.embedder)
        self.ingestion_service = build_ingestion_service(
            blob_document_loader=self.blob_document_loader,
            parsers=self.parsers,
            chunkers=self.chunkers,
            chroma_indexer=self.chroma_indexer,
        )
        self.reconciliation_service = build_reconciliation_service(
            blob_document_loader=self.blob_document_loader,
            blob_service=self.blob_service,
            chroma_indexer=self.chroma_indexer,
            settings=self.settings,
        )
        self.query_service = QueryService(retriever=self.retriever, settings=self.settings)
        self.draft_service = DraftService(query_service=self.query_service, settings=self.settings)
        self.health_service = HealthService(settings=self.settings)

    @classmethod
    def build(
        cls,
        settings: AppSettings | None = None,
        *,
        retriever: Retriever | None = None,
        env_file: Path | None = None,
        config_file: Path | None = None,
    ) -> "AppContainer":
        resolved_settings = settings or load_config(env_file=env_file, config_file=config_file)
        resolved_retriever = retriever or NullRetriever()
        return cls(settings=resolved_settings, retriever=resolved_retriever)
