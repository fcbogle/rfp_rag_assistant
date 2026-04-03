from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.chunkers import TenderDetailsChunker
from rfp_rag_assistant.models import ParsedDocument, ParsedSection


def test_tender_details_chunker_preserves_docx_section_context() -> None:
    chunker = TenderDetailsChunker(chunk_size_tokens=300, overlap_tokens=50)
    document = ParsedDocument(
        source_file=Path("section-b.docx"),
        file_type="docx",
        document_type="tender_details",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        sections=[
            ParsedSection(
                section_id="bidder-information",
                title="BIDDER INFORMATION",
                text="Provide the registered bidder details and related tender declarations.",
                kind="reference_content",
                heading_path=("SECTION B", "BIDDER INFORMATION"),
            )
        ],
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.document_type == "tender_details"
    assert "Heading path: SECTION B > BIDDER INFORMATION" in chunks[0].text


def test_tender_details_chunker_preserves_xlsx_sheet_metadata() -> None:
    chunker = TenderDetailsChunker(chunk_size_tokens=300, overlap_tokens=50)
    document = ParsedDocument(
        source_file=Path("evaluation.xlsx"),
        file_type="xlsx",
        document_type="tender_details",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        sections=[
            ParsedSection(
                section_id="evaluation-criteria-row-8",
                title="Evaluation Criteria row 8",
                text="This row captures an evaluation criterion and associated weighting guidance.",
                kind="spreadsheet_row",
                heading_path=("Evaluation Criteria",),
                structured_data={"sheet_name": "Evaluation Criteria", "row_index": 8},
            )
        ],
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.sheet_name == "Evaluation Criteria"
    assert chunks[0].metadata.extra["row_index"] == 8
