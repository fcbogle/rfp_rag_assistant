from pathlib import Path

from rfp_rag_assistant.parsers import ResponseSupportingMaterialExcelParser


def test_response_supporting_material_excel_parser_extracts_rows_from_real_workbook() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/2.6.1_Appendix_Mobilisation_Plan.xlsx"
    )

    parsed = ResponseSupportingMaterialExcelParser().parse_file(source)

    assert parsed.document_type == "response_supporting_material"
    assert parsed.metadata["subtype"] == "excel_supporting_material"
    assert parsed.metadata["sheet_count"] >= 3
    assert len(parsed.sections) > 0
    assert any(section.kind == "spreadsheet_row" for section in parsed.sections)
    assert any(section.structured_data.get("sheet_name") == "2 Mobilisation Plan " for section in parsed.sections)


def test_response_supporting_material_excel_parser_preserves_sheet_context_and_record_text() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/2.6.1_Appendix_Mobilisation_Plan.xlsx"
    )

    parsed = ResponseSupportingMaterialExcelParser().parse_file(source)

    first_row_section = next(section for section in parsed.sections if section.kind == "spreadsheet_row")
    assert first_row_section.heading_path
    assert "captures response supporting material" in first_row_section.text
    assert "Row values:" in first_row_section.text
