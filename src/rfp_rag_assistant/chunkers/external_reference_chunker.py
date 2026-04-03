from __future__ import annotations

from dataclasses import dataclass, field
import logging

from rfp_rag_assistant.chunkers.splitting import TextSplitter
from rfp_rag_assistant.models import Chunk, ChunkMetadata, ParsedDocument, ParsedSection, SourceReference


@dataclass(slots=True)
class ExternalReferenceChunker:
    chunk_size_tokens: int = 300
    overlap_tokens: int = 100
    default_chunk_type: str = "reference_content"
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))

    def chunk(self, document: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        for section in document.sections:
            chunks.extend(self._chunk_section(document, section))
        self.logger.info(
            "Chunked external reference file=%s sections=%s chunks=%s",
            document.source_file.name,
            len(document.sections),
            len(chunks),
        )
        return chunks

    def _chunk_section(self, document: ParsedDocument, section: ParsedSection) -> list[Chunk]:
        source_text = section.text.strip()
        if not source_text:
            return []

        content_segments = TextSplitter(
            chunk_size_tokens=self.chunk_size_tokens,
            overlap_tokens=self.overlap_tokens,
        ).split(source_text)
        chunk_total = len(content_segments)
        source_url = section.structured_data.get("source_url") or document.metadata.get("source_url")
        source_domain = section.structured_data.get("source_domain") or document.metadata.get("source_domain")
        reference_origin = section.structured_data.get("reference_origin") or document.metadata.get("reference_origin")

        return [
            Chunk(
                chunk_id=f"{section.section_id}-chunk-{index}",
                text=self._compose_chunk_text(section=section, content=segment),
                embedding_text=self._compose_chunk_text(section=section, content=segment),
                metadata=ChunkMetadata(
                    source_file=document.source_file,
                    file_type=document.file_type,
                    document_type=document.document_type,
                    chunk_type=section.kind or self.default_chunk_type,
                    heading_path=section.heading_path,
                    source_reference=SourceReference(
                        source_file=document.source_file,
                        file_type=document.file_type,
                        document_type=document.document_type,
                        heading_path=section.heading_path,
                        section_id=section.section_id,
                    ),
                    extra={
                        "section_id": section.section_id,
                        "section_title": section.title,
                        "section_title_normalized": section.structured_data.get("section_title_normalized"),
                        "page_title": section.structured_data.get("page_title"),
                        "source_url": source_url,
                        "source_domain": source_domain,
                        "reference_origin": reference_origin,
                        "chunk_index": index,
                        "chunk_total": chunk_total,
                    },
                ),
                structured_content={
                    "section_id": section.section_id,
                    "section_title": section.title,
                    "section_title_normalized": section.structured_data.get("section_title_normalized"),
                    "page_title": section.structured_data.get("page_title"),
                    "heading_path": list(section.heading_path),
                    "source_url": source_url,
                    "source_domain": source_domain,
                    "reference_origin": reference_origin,
                    "content_text": segment,
                    "chunk_index": index,
                    "chunk_total": chunk_total,
                },
            )
            for index, segment in enumerate(content_segments, start=1)
        ]

    def _compose_chunk_text(self, *, section: ParsedSection, content: str) -> str:
        parts: list[str] = []
        page_title = section.structured_data.get("page_title")
        if page_title:
            parts.append(f"Page: {page_title}")
        if section.title:
            parts.append(f"Section: {section.title}")
        parts.append(content)
        return "\n\n".join(part for part in parts if part).strip()
