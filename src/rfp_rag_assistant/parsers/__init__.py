"""Parsers for structure-aware document extraction."""

from .background_requirements_parser import BackgroundRequirementsParser
from .base import Parser
from .combined_qa_parser import CombinedQAParser
from .html_reference_parser import HTMLReferenceParser
from .itt_combined_qa_parser import ITTCombinedQAParser
from .narrative_combined_qa_parser import NarrativeCombinedQAParser
from .pdf_section_parser import PDFSectionParser
from .response_supporting_material_excel_parser import ResponseSupportingMaterialExcelParser
from .response_supporting_material_parser import ResponseSupportingMaterialParser
from .tender_details_parser import TenderDetailsParser

__all__ = [
    "BackgroundRequirementsParser",
    "CombinedQAParser",
    "HTMLReferenceParser",
    "ITTCombinedQAParser",
    "NarrativeCombinedQAParser",
    "Parser",
    "PDFSectionParser",
    "ResponseSupportingMaterialExcelParser",
    "ResponseSupportingMaterialParser",
    "TenderDetailsParser",
]
