from pathlib import Path
from datetime import UTC, datetime
import pytest

from rfp_rag_assistant.embeddings import chunk_to_chroma_record, flatten_chunk_metadata
from rfp_rag_assistant.models import Chunk, ChunkMetadata


def test_chroma_schema_flattens_combined_qa_metadata() -> None:
    chunk = Chunk(
        chunk_id="ITT01-chunk-1",
        text="Question metadata: ITT01 | Clinical Governance",
        embedding_text="Question metadata: ITT01 | Clinical Governance",
        metadata=ChunkMetadata(
            source_file=Path("ITT01-Clinical Governance-Blatchford.docx"),
            file_type="docx",
            document_type="combined_qa",
            chunk_type="qa_pair",
            extra={
                "section_title": "ITT01 - Clinical Governance",
                "question_id": "ITT01",
                "question_title": "Clinical Governance",
                "question_text": "Please describe your clinical governance arrangements.",
                "chunk_index": 1,
                "chunk_total": 2,
            },
        ),
        structured_content={
            "question_id": "ITT01",
            "question_title": "Clinical Governance",
            "question_text": "Please describe your clinical governance arrangements.",
        },
    )

    record = chunk_to_chroma_record(chunk)

    assert record.record_id == "ITT01-chunk-1"
    assert record.metadata["document_type"] == "combined_qa"
    assert record.metadata["question_id"] == "ITT01"
    assert record.metadata["question_title"] == "Clinical Governance"
    assert record.metadata["section_title"] == "ITT01 - Clinical Governance"


def test_chroma_schema_flattens_master_rfp_metadata() -> None:
    chunk = Chunk(
        chunk_id="ITT01-chunk-1",
        text="Question metadata: ITT01 | Clinical Governance",
        embedding_text="Question metadata: ITT01 | Clinical Governance",
        metadata=ChunkMetadata(
            source_file=Path("ITT01-Clinical Governance-Blatchford.docx"),
            file_type="docx",
            document_type="combined_qa",
            chunk_type="qa_pair",
            issuing_authority="Sussex Community NHS Foundation Trust",
            customer="Sussex Community NHS Foundation Trust",
            rfp_id="scft-wheelchair-2026",
            rfp_title="Wheelchair and Specialist Seating Service",
            extra={
                "section_title": "ITT01 - Clinical Governance",
                "question_id": "ITT01",
                "question_title": "Clinical Governance",
                "question_text": "Please describe your clinical governance arrangements.",
            },
        ),
        structured_content={
            "question_id": "ITT01",
            "question_title": "Clinical Governance",
            "question_text": "Please describe your clinical governance arrangements.",
        },
    )

    metadata = flatten_chunk_metadata(chunk)

    assert metadata["issuing_authority"] == "Sussex Community NHS Foundation Trust"
    assert metadata["customer"] == "Sussex Community NHS Foundation Trust"
    assert metadata["rfp_id"] == "scft-wheelchair-2026"
    assert metadata["rfp_title"] == "Wheelchair and Specialist Seating Service"


def test_chroma_schema_flattens_blob_version_metadata() -> None:
    chunk = Chunk(
        chunk_id="ITT01-chunk-1",
        text="Question metadata: ITT01 | Clinical Governance",
        embedding_text="Question metadata: ITT01 | Clinical Governance",
        metadata=ChunkMetadata(
            source_file=Path("combined_qa/ITT01-Clinical Governance-Blatchford.docx"),
            file_type="docx",
            document_type="combined_qa",
            chunk_type="qa_pair",
            blob_name="combined_qa/ITT01-Clinical Governance-Blatchford.docx",
            blob_etag="etag-xyz",
            blob_last_modified=datetime(2026, 4, 6, 10, 30, tzinfo=UTC),
            blob_content_length=8192,
            ingested_at=datetime(2026, 4, 6, 10, 45, tzinfo=UTC),
            extra={
                "section_title": "ITT01 - Clinical Governance",
                "question_id": "ITT01",
                "question_title": "Clinical Governance",
                "question_text": "Please describe your clinical governance arrangements.",
            },
        ),
        structured_content={
            "question_id": "ITT01",
            "question_title": "Clinical Governance",
            "question_text": "Please describe your clinical governance arrangements.",
        },
    )

    metadata = flatten_chunk_metadata(chunk)

    assert metadata["blob_name"] == "combined_qa/ITT01-Clinical Governance-Blatchford.docx"
    assert metadata["blob_etag"] == "etag-xyz"
    assert metadata["blob_last_modified"] == "2026-04-06T10:30:00+00:00"
    assert metadata["blob_content_length"] == 8192
    assert metadata["ingested_at"] == "2026-04-06T10:45:00+00:00"


def test_chroma_schema_flattens_response_supporting_material_spreadsheet_metadata() -> None:
    chunk = Chunk(
        chunk_id="mobilisation-team-row-6-chunk-1",
        text="Sheet context: 1 Mobilisation Team",
        embedding_text="Sheet context: 1 Mobilisation Team",
        metadata=ChunkMetadata(
            source_file=Path("2.6.1_Appendix_Mobilisation_Plan.xlsx"),
            file_type="xlsx",
            document_type="response_supporting_material",
            chunk_type="spreadsheet_row_group",
            sheet_name="1 Mobilisation Team",
            extra={
                "section_title": "1 Mobilisation Team profile - Beth Pitcairn",
                "chunk_index": 1,
                "chunk_total": 1,
            },
        ),
        structured_content={
            "sheet_name": "1 Mobilisation Team",
            "section_title": "1 Mobilisation Team profile - Beth Pitcairn",
        },
    )

    metadata = flatten_chunk_metadata(chunk)

    assert metadata["document_type"] == "response_supporting_material"
    assert metadata["sheet_name"] == "1 Mobilisation Team"
    assert metadata["section_title"] == "1 Mobilisation Team profile - Beth Pitcairn"


def test_chroma_schema_flattens_external_reference_provenance() -> None:
    chunk = Chunk(
        chunk_id="core20plus5-approach-chunk-1",
        text="Page: NHS England",
        embedding_text="Page: NHS England",
        metadata=ChunkMetadata(
            source_file=Path("external_reference/www.england.nhs.uk/core20plus5.html"),
            file_type="html",
            document_type="external_reference",
            chunk_type="reference_content",
            extra={
                "section_title": "Core20PLUS5",
                "source_url": "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
                "source_domain": "www.england.nhs.uk",
                "reference_origin": "customer_cited",
            },
        ),
        structured_content={
            "section_title": "Core20PLUS5",
            "source_url": "https://www.england.nhs.uk/about/equality/equality-hub/core20plus5/",
            "source_domain": "www.england.nhs.uk",
            "reference_origin": "customer_cited",
        },
    )

    record = chunk_to_chroma_record(chunk)

    assert record.metadata["source_url"].startswith("https://www.england.nhs.uk/")
    assert record.metadata["source_domain"] == "www.england.nhs.uk"
    assert record.metadata["reference_origin"] == "customer_cited"


def test_chroma_schema_rejects_missing_required_combined_qa_fields() -> None:
    chunk = Chunk(
        chunk_id="bad-chunk",
        text="Answer only",
        embedding_text="Answer only",
        metadata=ChunkMetadata(
            source_file=Path("bad.docx"),
            file_type="docx",
            document_type="combined_qa",
            chunk_type="qa_pair",
            extra={"section_title": "Bad"},
        ),
    )

    with pytest.raises(ValueError, match="Missing required Chroma metadata fields for combined_qa"):
        chunk_to_chroma_record(chunk)
