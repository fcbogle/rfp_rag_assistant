from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import ParsedDocument
from rfp_rag_assistant.parsers.background_requirements_parser import BackgroundRequirementsParser
from rfp_rag_assistant.parsers.pdf_section_parser import PDFSectionParser
from rfp_rag_assistant.parsers.response_supporting_material_excel_parser import (
    ResponseSupportingMaterialExcelParser,
)


@dataclass(slots=True)
class TenderDetailsParser:
    document_type: str = "tender_details"

    def parse(self, document: LoadedDocument) -> ParsedDocument:
        source_file = Path(document.payload) if isinstance(document.payload, (str, Path)) else document.source_file
        return self.parse_file(source_file)

    def parse_file(self, source_file: Path) -> ParsedDocument:
        suffix = source_file.suffix.lower()
        if suffix == ".docx":
            parsed = BackgroundRequirementsParser(document_type=self.document_type).parse_file(source_file)
            parsed.metadata["subtype"] = "word_tender_details"
            return parsed
        if suffix == ".xlsx":
            parsed = ResponseSupportingMaterialExcelParser(document_type=self.document_type).parse_file(source_file)
            parsed.metadata["subtype"] = "excel_tender_details"
            return parsed
        if suffix == ".pdf":
            return PDFSectionParser(
                document_type=self.document_type,
                subtype="pdf_tender_details",
            ).parse_file(source_file)
        raise ValueError(f"Tender details parser does not support file type: {suffix}")
