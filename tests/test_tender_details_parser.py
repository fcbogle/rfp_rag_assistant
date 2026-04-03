from pathlib import Path

from rfp_rag_assistant.parsers import TenderDetailsParser


def test_tender_details_parser_extracts_real_docx() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "4. SCFT - Prosthetic, orthotic and technician services & products - ITT Section B vDraft.docx"
    )

    parsed = TenderDetailsParser().parse_file(source)

    assert parsed.document_type == "tender_details"
    assert parsed.metadata["subtype"] == "word_tender_details"
    assert len(parsed.sections) >= 5
    assert any(section.title == "Supplier Details" for section in parsed.sections)
    assert any("BIDDER INFORMATION" in section.heading_path for section in parsed.sections)


def test_tender_details_parser_extracts_real_xlsx() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "9. SCFT - Prosthetic, orthotic and technician services & products - ITT Evaluation and Weighting matrix vDraft.xlsx"
    )

    parsed = TenderDetailsParser().parse_file(source)

    assert parsed.document_type == "tender_details"
    assert parsed.metadata["subtype"] == "excel_tender_details"
    assert len(parsed.sections) > 0
    assert any(section.kind == "spreadsheet_row" for section in parsed.sections)


def test_tender_details_parser_extracts_real_pdf() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "3. SCFT - Prosthetic, orthotic and technician services & products - ITT Section A vFinal.pdf"
    )

    parsed = TenderDetailsParser().parse_file(source)

    assert parsed.document_type == "tender_details"
    assert parsed.metadata["subtype"] == "pdf_tender_details"
    assert any(section.title == "INTRODUCTION AND BACKGROUND" for section in parsed.sections)
