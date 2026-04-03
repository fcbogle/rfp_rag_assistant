from pathlib import Path

from rfp_rag_assistant.parsers import ResponseSupportingMaterialParser


def test_response_supporting_material_parser_extracts_real_pdf() -> None:
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/"
        "2.3.12_Appendix_Patient_Safety_Incident_Response_Framework_Policy.pdf"
    )

    parsed = ResponseSupportingMaterialParser().parse_file(source)

    assert parsed.document_type == "response_supporting_material"
    assert parsed.metadata["subtype"] == "pdf_supporting_material"
    assert any(section.title == "1 Introduction and Purpose" for section in parsed.sections)
