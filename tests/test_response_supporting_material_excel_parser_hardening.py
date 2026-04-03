from pathlib import Path

from rfp_rag_assistant.parsers import ResponseSupportingMaterialExcelParser


def test_response_supporting_material_excel_parser_extracts_profile_sections_from_real_workbook() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/2.6.1_Appendix_Mobilisation_Plan.xlsx"
    )

    parsed = ResponseSupportingMaterialExcelParser().parse_file(source)

    profile_sections = [section for section in parsed.sections if section.kind == "spreadsheet_row_group"]

    assert profile_sections
    assert any("Beth Pitcairn" in section.title for section in profile_sections)
    assert any("captures authored supporting material" in section.text for section in profile_sections)
    assert any("Responsibilities:" in section.text for section in profile_sections)
