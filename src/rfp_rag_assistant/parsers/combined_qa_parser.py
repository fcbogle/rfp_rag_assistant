from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument
from rfp_rag_assistant.parsers.itt_combined_qa_parser import ITTCombinedQAParser
from rfp_rag_assistant.parsers.narrative_combined_qa_parser import NarrativeCombinedQAParser


@dataclass(slots=True)
class CombinedQAParser:
    document_type: str = "combined_qa"

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        source_file = Path(document.payload) if isinstance(document.payload, (str, Path)) else document.source_file
        return self.parse_file(source_file)

    def parse_file(self, source_file: Path) -> ParsedDocument:
        if source_file.suffix.lower() != ".docx":
            raise ValueError(f"Combined QA parser does not support file type: {source_file.suffix.lower()}")
        if source_file.stem.upper().startswith("ITT"):
            return ITTCombinedQAParser(document_type=self.document_type).parse_file(source_file)
        return NarrativeCombinedQAParser(document_type=self.document_type).parse_file(source_file)
