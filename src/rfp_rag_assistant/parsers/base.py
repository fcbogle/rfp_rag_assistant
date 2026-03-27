from __future__ import annotations

from typing import Protocol

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument


class Parser(Protocol):
    def parse(self, document: LoadedDocument) -> ParsedDocument:
        """Convert loaded content into a structured intermediate representation."""
