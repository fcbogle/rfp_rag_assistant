from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.chunkers import ITTCombinedQAChunker
from rfp_rag_assistant.models import ParsedDocument, ParsedSection


def _build_document(*, answer_text: str) -> ParsedDocument:
    return ParsedDocument(
        source_file=Path("ITT01-Clinical Governance-Blatchford.docx"),
        file_type="docx",
        document_type="combined_qa",
        extracted_at=datetime(2026, 4, 2, 12, 0, 0),
        metadata={
            "question_id": "ITT01",
            "question_title": "Clinical Governance",
        },
        sections=[
            ParsedSection(
                section_id="ITT01",
                title="ITT01 - Clinical Governance",
                text=answer_text,
                kind="qa_pair",
                structured_data={
                    "question_id": "ITT01",
                    "question_title": "Clinical Governance",
                    "question_text": "Please describe your clinical governance arrangements.",
                    "answer_text": answer_text,
                },
            )
        ],
    )


def test_itt_combined_qa_chunker_keeps_question_metadata_on_single_chunk() -> None:
    chunker = ITTCombinedQAChunker(chunk_size_tokens=300, overlap_tokens=50)
    document = _build_document(
        answer_text="Blatchford maintains a robust clinical governance framework with clear accountability."
    )

    chunks = chunker.chunk(document)

    assert len(chunks) == 1
    assert chunks[0].metadata.chunk_type == "qa_pair"
    assert chunks[0].metadata.extra["question_id"] == "ITT01"
    assert chunks[0].metadata.extra["question_title"] == "Clinical Governance"
    assert "Question metadata: ITT01 | Clinical Governance" in chunks[0].text
    assert "Question: Please describe your clinical governance arrangements." in chunks[0].text
    assert "Answer: Blatchford maintains a robust clinical governance framework" in chunks[0].text


def test_itt_combined_qa_chunker_splits_long_answer_and_preserves_traceability() -> None:
    chunker = ITTCombinedQAChunker(chunk_size_tokens=60, overlap_tokens=15)
    long_answer = "\n\n".join(
        [
            " ".join(["Clinical governance arrangements are reviewed regularly to ensure safe and effective care."] * 4),
            " ".join(["The service uses audit, incident review, and multidisciplinary oversight to improve outcomes."] * 4),
            " ".join(["Policies are maintained, approved, and communicated through formal governance channels."] * 4),
        ]
    )
    document = _build_document(answer_text=long_answer)

    chunks = chunker.chunk(document)

    assert len(chunks) > 1
    assert all(chunk.metadata.extra["chunk_total"] == len(chunks) for chunk in chunks)
    assert [chunk.metadata.extra["chunk_index"] for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert all(chunk.structured_content["question_id"] == "ITT01" for chunk in chunks)
    assert all("Question metadata: ITT01 | Clinical Governance" in chunk.text for chunk in chunks)
    assert all("Question: Please describe your clinical governance arrangements." in chunk.text for chunk in chunks)
    assert all(chunk.metadata.source_reference is not None for chunk in chunks)
