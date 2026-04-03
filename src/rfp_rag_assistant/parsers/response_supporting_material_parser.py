from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument
from rfp_rag_assistant.parsers.pdf_section_parser import PDFSectionParser
from rfp_rag_assistant.parsers.response_supporting_material_excel_parser import (
    ResponseSupportingMaterialExcelParser,
)


@dataclass(slots=True)
class ResponseSupportingMaterialParser:
    document_type: str = "response_supporting_material"

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        source_file = Path(document.payload) if isinstance(document.payload, (str, Path)) else document.source_file
        return self.parse_file(source_file)

    def parse_file(self, source_file: Path) -> ParsedDocument:
        suffix = source_file.suffix.lower()
        if suffix == ".xlsx":
            return ResponseSupportingMaterialExcelParser(document_type=self.document_type).parse_file(source_file)
        if suffix == ".pdf":
            return PDFSectionParser(
                document_type=self.document_type,
                subtype="pdf_supporting_material",
            ).parse_file(source_file)
        raise ValueError(f"Response supporting material parser does not support file type: {suffix}")
