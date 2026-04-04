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


def test_pdf_section_parser_marks_image_only_pdf_for_ocr() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/"
        "2.4.2_Appendix_Blatchford _SMARTSTEP_Overview.pdf"
    )

    parsed = PDFSectionParser(
        document_type="response_supporting_material",
        subtype="pdf_supporting_material",
    ).parse_file(source)

    assert parsed.metadata["image_only_pdf"] is True
    assert parsed.metadata["ocr_required"] is True
    assert parsed.metadata["empty_text_pages"] == parsed.metadata["page_count"]
    assert parsed.sections == []
