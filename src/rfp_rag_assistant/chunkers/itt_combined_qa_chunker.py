from __future__ import annotations

from dataclasses import dataclass, field
import logging

from rfp_rag_assistant.chunkers.ids import build_chunk_id
from rfp_rag_assistant.models import Chunk, ChunkMetadata, ParsedDocument, ParsedSection, SourceReference
from rfp_rag_assistant.chunkers.splitting import TextSplitter


@dataclass(slots=True)
class ITTCombinedQAChunker:
    chunk_size_tokens: int = 300
    overlap_tokens: int = 100
    chunk_type: str = "qa_pair"
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []

        for section in document.sections:
            if section.kind != "qa_pair":
                continue
            chunks.extend(self._chunk_section(document, section))

        self.logger.info(
            "Chunked combined QA file=%s sections=%s chunks=%s",
            document.source_file.name,
            len([section for section in document.sections if section.kind == "qa_pair"]),
            len(chunks),
        )

        return chunks

    def _chunk_section(self, document: ParsedDocument, section: ParsedSection) -> list[Chunk]:
        question_id = str(section.structured_data.get("question_id", "")).strip()
        question_title = str(section.structured_data.get("question_title", "")).strip()
        question_text = str(section.structured_data.get("question_text", "")).strip()
        answer_text = str(section.structured_data.get("answer_text", section.text)).strip()
        if not answer_text:
            return []

        answer_segments = TextSplitter(
            chunk_size_tokens=self.chunk_size_tokens,
            overlap_tokens=self.overlap_tokens,
        ).split(answer_text)
        chunk_total = len(answer_segments)
        chunk_texts = [
            self._compose_chunk_text(
                question_id=question_id,
                question_title=question_title,
                question_text=question_text,
                answer_text=answer_segment,
            )
            for answer_segment in answer_segments
        ]

        return [
            Chunk(
                chunk_id=build_chunk_id(document.source_file, section.section_id or question_id or "qa", index),
                text=chunk_text,
                embedding_text=chunk_text,
                metadata=ChunkMetadata(
                    source_file=document.source_file,
                    file_type=document.file_type,
                    document_type=document.document_type,
                    chunk_type=self.chunk_type,
                    heading_path=section.heading_path,
                    source_reference=SourceReference(
                        source_file=document.source_file,
                        file_type=document.file_type,
                        document_type=document.document_type,
                        heading_path=section.heading_path,
                        section_id=section.section_id,
                    ),
                    extra={
                        "question_id": question_id,
                        "question_title": question_title,
                        "question_text": question_text,
                        "section_title": section.title,
                        "chunk_index": index,
                        "chunk_total": chunk_total,
                    },
                ),
                structured_content={
                    "question_id": question_id,
                    "question_title": question_title,
                    "question_text": question_text,
                    "answer_text": answer_segment,
                    "chunk_index": index,
                    "chunk_total": chunk_total,
                },
            )
            for index, (chunk_text, answer_segment) in enumerate(zip(chunk_texts, answer_segments), start=1)
        ]

    def _compose_chunk_text(
        self,
        *,
        question_id: str,
        question_title: str,
        question_text: str,
        answer_text: str,
    ) -> str:
        parts = []
        if question_id or question_title:
            parts.append("Question metadata: " + " | ".join(part for part in (question_id, question_title) if part))
        if question_text:
            parts.append(f"Question: {question_text}")
        if answer_text:
            parts.append(f"Answer: {answer_text}")
        return "\n\n".join(parts).strip()
