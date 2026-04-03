from pathlib import Path

from rfp_rag_assistant.app.pipeline import IngestionPipeline
from rfp_rag_assistant.chunkers import ResponseSupportingMaterialChunker
from rfp_rag_assistant.loaders import LocalDocumentLoader
from rfp_rag_assistant.parsers import ResponseSupportingMaterialParser


def test_supporting_material_pipeline_ingests_real_workbook() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=ResponseSupportingMaterialParser(),
        chunker=ResponseSupportingMaterialChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/2.6.1_Appendix_Mobilisation_Plan.xlsx"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "response_supporting_material"
    assert len(parsed.sections) > 0
    assert len(chunks) >= len(parsed.sections)
    assert any(chunk.metadata.sheet_name == "1 Mobilisation Team" for chunk in chunks)


def test_supporting_material_pipeline_ingests_real_pdf() -> None:
    pipeline = IngestionPipeline(
        loader=LocalDocumentLoader(),
        parser=ResponseSupportingMaterialParser(),
        chunker=ResponseSupportingMaterialChunker(chunk_size_tokens=300, overlap_tokens=50),
    )
    source = Path(
        "/Users/frankbogle/Documents/RFP/response_supporting_material/"
        "2.3.12_Appendix_Patient_Safety_Incident_Response_Framework_Policy.pdf"
    )

    parsed, chunks = pipeline.ingest(source)

    assert parsed.document_type == "response_supporting_material"
    assert len(parsed.sections) > 0
    assert len(chunks) >= len(parsed.sections)
