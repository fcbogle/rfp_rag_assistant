from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.chunkers import ExternalReferenceChunker
from rfp_rag_assistant.models import ParsedDocument, ParsedSection


def test_external_reference_chunker_keeps_url_provenance() -> None:
    document = ParsedDocument(
        source_file=Path("external_reference/www.england.nhs.uk/core20plus5.html"),
        file_type="html",
        document_type="external_reference",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        metadata={
            "source_url": "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
            "source_domain": "www.england.nhs.uk",
            "reference_origin": "customer_cited",
        },
        sections=[
            ParsedSection(
                section_id="approach",
                title="Approach",
                text="Providers should focus on the most deprived populations and use data to prioritise interventions.",
                kind="reference_content",
                heading_path=("Approach",),
                structured_data={
                    "page_title": "Core20PLUS5 Guidance",
                    "section_title_normalized": "Approach",
                    "source_url": "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
                    "source_domain": "www.england.nhs.uk",
                    "reference_origin": "customer_cited",
                },
            )
        ],
    )

    chunks = ExternalReferenceChunker(chunk_size_tokens=300, overlap_tokens=50).chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.extra["source_domain"] == "www.england.nhs.uk"
    assert chunks[0].metadata.extra["reference_origin"] == "customer_cited"
    assert "Page: Core20PLUS5 Guidance" in chunks[0].text
    assert chunks[0].structured_content["source_url"].startswith("https://www.england.nhs.uk/")
