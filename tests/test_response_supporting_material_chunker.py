from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.chunkers import ResponseSupportingMaterialChunker
from rfp_rag_assistant.models import ParsedDocument, ParsedSection


def _build_document(*, text: str) -> ParsedDocument:
    return ParsedDocument(
        source_file=Path("2.6.1_Appendix_Mobilisation_Plan.xlsx"),
        file_type="xlsx",
        document_type="response_supporting_material",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        sections=[
            ParsedSection(
                section_id="mobilisation-team-row-6",
                title="1 Mobilisation Team row 6",
                text=text,
                kind="spreadsheet_row",
                heading_path=("1 Mobilisation Team",),
                structured_data={
                    "sheet_name": "1 Mobilisation Team",
                    "row_index": 6,
                },
            )
        ],
    )


def test_response_supporting_material_chunker_preserves_sheet_metadata() -> None:
    chunker = ResponseSupportingMaterialChunker(chunk_size_tokens=300, overlap_tokens=50)
    document = _build_document(
        text="This row from sheet '1 Mobilisation Team' captures key mobilisation contacts and roles."
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.chunk_type == "spreadsheet_row"
    assert chunks[0].metadata.sheet_name == "1 Mobilisation Team"
    assert chunks[0].metadata.extra["row_index"] == 6
    assert "Sheet context: 1 Mobilisation Team" in chunks[0].text


def test_response_supporting_material_chunker_splits_long_rows() -> None:
    chunker = ResponseSupportingMaterialChunker(chunk_size_tokens=60, overlap_tokens=15)
    long_text = "\n\n".join(
        [
            " ".join(["This mobilisation activity row describes delivery ownership, expected outputs, and escalation controls."] * 4),
            " ".join(["It also captures implementation timing, dependencies, and governance checkpoints."] * 4),
            " ".join(["The workbook row provides supporting material for service transition readiness."] * 4),
        ]
    )
    document = _build_document(text=long_text)

    chunks = chunker.chunk(document)

    assert len(chunks) > 1
    assert all(chunk.metadata.sheet_name == "1 Mobilisation Team" for chunk in chunks)
    assert all(chunk.metadata.extra["chunk_total"] == len(chunks) for chunk in chunks)
    assert all(chunk.structured_content["row_index"] == 6 for chunk in chunks)
