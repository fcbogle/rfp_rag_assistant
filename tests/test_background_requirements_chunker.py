from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.chunkers import BackgroundRequirementsChunker
from rfp_rag_assistant.models import ParsedDocument, ParsedSection


def _build_document(*, section_text: str) -> ParsedDocument:
    return ParsedDocument(
        source_file=Path("Background info - SWS v4.docx"),
        file_type="docx",
        document_type="background_requirements",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        sections=[
            ParsedSection(
                section_id="service-overview",
                title="Service Overview",
                text=section_text,
                kind="reference_content",
                heading_path=("Background", "Service Overview"),
            )
        ],
    )


def test_background_requirements_chunker_keeps_section_context() -> None:
    chunker = BackgroundRequirementsChunker(chunk_size_tokens=300, overlap_tokens=50)
    document = _build_document(
        section_text="The Sussex Wheelchair Service supports adults and children across the region."
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.chunk_type == "reference_content"
    assert chunks[0].metadata.heading_path == ("Background", "Service Overview")
    assert chunks[0].metadata.extra["section_title"] == "Service Overview"
    assert "Heading path: Background > Service Overview" in chunks[0].text
    assert "Section: Service Overview" in chunks[0].text


def test_background_requirements_chunker_splits_long_sections() -> None:
    chunker = BackgroundRequirementsChunker(chunk_size_tokens=60, overlap_tokens=15)
    long_text = "\n\n".join(
        [
            " ".join(["The service specification sets out required pathways, referral routes, and governance expectations."] * 4),
            " ".join(["Providers must demonstrate multidisciplinary delivery, risk controls, and audit capability."] * 4),
            " ".join(["Commissioners expect clear escalation, incident reporting, and performance management arrangements."] * 4),
        ]
    )
    document = _build_document(section_text=long_text)

    chunks = chunker.chunk(document)

    assert len(chunks) > 1
    assert all(chunk.metadata.extra["chunk_total"] == len(chunks) for chunk in chunks)
    assert [chunk.metadata.extra["chunk_index"] for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert all(chunk.structured_content["section_id"] == "service-overview" for chunk in chunks)
    assert all("Section: Service Overview" in chunk.text for chunk in chunks)
