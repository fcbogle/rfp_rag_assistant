from pathlib import Path

from rfp_rag_assistant.parsers import CombinedQAParser, NarrativeCombinedQAParser


def test_narrative_combined_qa_parser_extracts_question_and_answer_from_real_file() -> None:
    source = Path("/Users/frankbogle/Documents/RFP/combined_qa/2.2 CONTRACTS AND FEEDBACK Final.docx")

    parsed = NarrativeCombinedQAParser().parse_file(source)

    assert parsed.document_type == "combined_qa"
    assert parsed.metadata["subtype"] == "narrative_combined_qa"
    assert parsed.metadata["question_id"] == "2.2"
    assert "CONTRACTS AND FEEDBACK" in parsed.metadata["question_title"]
    section = parsed.sections[0]
    assert section.kind == "qa_pair"
    assert "Please provide details of contracts you have had in place" in section.structured_data["question_text"]
    assert "Blatchford has held contracts for 26 separate services" in section.structured_data["answer_text"]
    assert section.structured_data["answer_paragraph_count"] >= 3


def test_combined_qa_parser_dispatches_narrative_file() -> None:
    source = Path("/Users/frankbogle/Documents/RFP/combined_qa/2.3.4 STAFFING Final.docx")

    parsed = CombinedQAParser().parse_file(source)

    assert parsed.metadata["subtype"] == "narrative_combined_qa"
    assert parsed.sections[0].kind == "qa_pair"
    assert "Please describe how you intend to meet the requirements" in parsed.sections[0].structured_data["question_text"]
