"""Embedding preparation and vector provider interfaces."""

from .azure_openai_embedder import AzureOpenAIEmbedder
from .chroma_indexer import ChromaIndexer, IndexedCollectionResult, IndexingSummary
from .base import Embedder
from .chroma_schema import ChromaRecord, DOCUMENT_TYPE_SCHEMAS, chunk_to_chroma_record, flatten_chunk_metadata

__all__ = [
    "AzureOpenAIEmbedder",
    "ChromaIndexer",
    "ChromaRecord",
    "DOCUMENT_TYPE_SCHEMAS",
    "Embedder",
    "IndexedCollectionResult",
    "IndexingSummary",
    "chunk_to_chroma_record",
    "flatten_chunk_metadata",
]
