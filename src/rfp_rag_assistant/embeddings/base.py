from __future__ import annotations

from typing import Protocol

from rfp_rag_assistant.models import Chunk


class Embedder(Protocol):
    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        """Generate vector embeddings for prepared chunks."""
