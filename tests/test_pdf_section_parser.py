from pathlib import Path

from rfp_rag_assistant.parsers import PDFSectionParser


def test_pdf_section_parser_extracts_tender_sections_from_real_pdf() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "3. SCFT - Prosthetic, orthotic and technician services & products - ITT Section A vFinal.pdf"
    )

    parsed = PDFSectionParser(document_type="tender_details", subtype="pdf_tender_details").parse_file(source)

    assert parsed.document_type == "tender_details"
    assert parsed.metadata["subtype"] == "pdf_tender_details"
    assert len(parsed.sections) >= 3
    assert any(section.title == "INTRODUCTION AND BACKGROUND" for section in parsed.sections)
    intro = next(section for section in parsed.sections if section.title == "INTRODUCTION AND BACKGROUND")
    assert intro.structured_data["section_title_normalized"] == "Introduction and Background"


def test_pdf_section_parser_extracts_supporting_material_sections_from_real_pdf() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/"
        "2.3.12_Appendix_Patient_Safety_Incident_Response_Framework_Policy.pdf"
    )

    parsed = PDFSectionParser(
        document_type="response_supporting_material",
        subtype="pdf_supporting_material",
    ).parse_file(source)

    assert parsed.document_type == "response_supporting_material"
    assert len(parsed.sections) >= 5
    assert any(section.title == "1 Introduction and Purpose" for section in parsed.sections)
