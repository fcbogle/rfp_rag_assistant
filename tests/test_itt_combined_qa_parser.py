from pathlib import Path

from rfp_rag_assistant.parsers.itt_combined_qa_parser import ITTCombinedQAParser


def test_itt_parser_extracts_question_and_answer_from_structured_file() -> None:
    parser = ITTCombinedQAParser()
    source = Path("/Users/frankbogle/Documents/RFP/combined_qa/ITT01-Clinical Governance-Blatchford.docx")

    parsed = parser.parse_file(source)

    assert parsed.document_type == "combined_qa"
    assert parsed.metadata["subtype"] == "itt_structured_qa"
    assert parsed.metadata["question_id"] == "ITT01"
    assert parsed.metadata["question_title"] == "Clinical Governance"

    section = parsed.sections[0]
    assert section.kind == "qa_pair"
    assert section.structured_data["question_id"] == "ITT01"
    assert "Describe your organisation’s proposed framework" in section.structured_data["question_text"]
    assert "Our clinical governance framework provides NHS Sussex ICB" in section.structured_data["answer_text"]


def test_itt_parser_extracts_another_structured_question() -> None:
    parser = ITTCombinedQAParser()
    source = Path("/Users/frankbogle/Documents/RFP/combined_qa/ITT03-Waiting List Management-Blatchford.docx")

    parsed = parser.parse_file(source)

    section = parsed.sections[0]
    assert parsed.metadata["question_id"] == "ITT03"
    assert parsed.metadata["question_title"] == "Waiting list management"
    assert "Describe and explain your strategies and practical steps" in section.structured_data["question_text"]
    assert len(section.structured_data["answer_text"]) > 500
