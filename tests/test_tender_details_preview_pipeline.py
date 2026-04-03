from pathlib import Path

from rfp_rag_assistant.app.pipeline import IngestionPipeline
from rfp_rag_assistant.chunkers import TenderDetailsChunker
from rfp_rag_assistant.loaders import LocalDocumentLoader
from rfp_rag_assistant.parsers import TenderDetailsParser


def test_tender_details_pipeline_ingests_real_docx() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=TenderDetailsParser(),
        chunker=TenderDetailsChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "4. SCFT - Prosthetic, orthotic and technician services & products - ITT Section B vDraft.docx"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "tender_details"
    assert len(parsed.sections) > 0
    assert len(chunks) >= len(parsed.sections)


def test_tender_details_pipeline_ingests_real_xlsx() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=TenderDetailsParser(),
        chunker=TenderDetailsChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "9. SCFT - Prosthetic, orthotic and technician services & products - ITT Evaluation and Weighting matrix vDraft.xlsx"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "tender_details"
    assert len(parsed.sections) > 0
    assert any(chunk.metadata.sheet_name == "Evaluation Criteria" for chunk in chunks)


def test_tender_details_pipeline_ingests_real_pdf() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=TenderDetailsParser(),
        chunker=TenderDetailsChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/tender_details/"
        "3. SCFT - Prosthetic, orthotic and technician services & products - ITT Section A vFinal.pdf"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "tender_details"
    assert len(parsed.sections) > 0
    assert len(chunks) >= len(parsed.sections)
