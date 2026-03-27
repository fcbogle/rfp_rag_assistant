from datetime import date, datetime
from pathlib import Path

from rfp_rag_assistant.models import Chunk, ChunkMetadata, ParsedDocument, ParsedSection


def test_parsed_document_holds_sections() -> None:
    document = ParsedDocument(
        source_file=Path("sample.docx"),
        file_type="docx",
        document_type="rfp_response",
        extracted_at=datetime(2026, 1, 1, 12, 0, 0),
        sections=[
            ParsedSection(
                section_id="sec-1",
                title="Security",
                text="We provide encryption at rest.",
                kind="capability_statement",
                heading_path=("Security",),
            )
        ],
    )

    assert document.sections[0].heading_path == ("Security",)


def test_chunk_metadata_preserves_traceability_fields() -> None:
    chunk = Chunk(
        chunk_id="chunk-1",
        text="Approved prior answer",
        embedding_text="Approved prior answer",
        metadata=ChunkMetadata(
            source_file=Path("answers.xlsx"),
            file_type="xlsx",
            document_type="historical_answers",
            chunk_type="spreadsheet_row",
            sheet_name="Security Responses",
            customer="Example Co",
            date=date(2025, 12, 31),
            reusable_flag=True,
            approval_status="approved",
        ),
    )

    assert chunk.metadata.sheet_name == "Security Responses"
    assert chunk.metadata.reusable_flag is True
