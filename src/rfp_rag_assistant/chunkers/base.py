from __future__ import annotations

from typing import Protocol

from rfp_rag_assistant.models import Chunk, ParsedDocument


class Chunker(Protocol):
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        """Create embedding-ready chunks from a parsed document."""
