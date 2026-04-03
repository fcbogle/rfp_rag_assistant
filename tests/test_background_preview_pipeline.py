from pathlib import Path

from rfp_rag_assistant.app.pipeline import IngestionPipeline
from rfp_rag_assistant.chunkers import BackgroundRequirementsChunker
from rfp_rag_assistant.loaders import LocalDocumentLoader
from rfp_rag_assistant.parsers import BackgroundRequirementsParser


def test_background_requirements_pipeline_ingests_real_document() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=BackgroundRequirementsParser(),
        chunker=BackgroundRequirementsChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/background_requirements/"
        "Background information - Wheelchair and Specialist Seating Service.docx"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "background_requirements"
    assert len(parsed.sections) >= 5
    assert len(chunks) >= len(parsed.sections)
    assert any(chunk.metadata.extra["section_title"] == "Current services" for chunk in chunks)
