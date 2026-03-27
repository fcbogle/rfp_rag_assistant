from datetime import datetime
from pathlib import Path

from rfp_rag_assistant.app.pipeline import IngestionPipeline
from rfp_rag_assistant.loaders import LoadedDocument
from rfp_rag_assistant.models import Chunk, ChunkMetadata, ParsedDocument, ParsedSection


class StubLoader:
    def load(self, source_file: Path) -> LoadedDocument:
        return LoadedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip("."),
            payload={"text": "Question: Describe your controls."},
        )


class StubParser:
    def parse(self, document: LoadedDocument) -> ParsedDocument:
        return ParsedDocument(
            source_file=document.source_file,
            file_type=document.file_type,
            document_type="rfp_response",
            extracted_at=datetime(2026, 1, 1, 0, 0, 0),
            sections=[
                ParsedSection(
                    section_id="qa-1",
                    title="Security",
                    text="Question: Describe your controls. Answer: Approved response.",
                    kind="qa_pair",
                    heading_path=("Security",),
                )
            ],
        )


class StubChunker:
    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        return [
            Chunk(
                chunk_id="chunk-qa-1",
                text=document.sections[0].text,
                embedding_text=document.sections[0].text,
                metadata=ChunkMetadata(
                    source_file=document.source_file,
                    file_type=document.file_type,
                    document_type=document.document_type,
                    chunk_type="qa_pair",
                    heading_path=document.sections[0].heading_path,
                ),
            )
        ]


def test_ingestion_pipeline_returns_parsed_document_and_chunks() -> None:
    pipeline = IngestionPipeline(
        loader=StubLoader(),
        parser=StubParser(),
        chunker=StubChunker(),
    )

    parsed, chunks = pipeline.ingest(Path("example.docx"))

    assert parsed.sections[0].kind == "qa_pair"
    assert chunks[0].metadata.heading_path == ("Security",)
