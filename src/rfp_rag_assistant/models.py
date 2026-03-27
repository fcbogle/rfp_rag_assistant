from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class SourceReference:
    source_file: Path
    file_type: str
    document_type: str
    sheet_name: str | None = None
    heading_path: tuple[str, ...] = ()
    row_index: int | None = None
    section_id: str | None = None


@dataclass(slots=True)
class ChunkMetadata:
    source_file: Path
    file_type: str
    document_type: str
    chunk_type: str
    customer: str | None = None
    date: date | None = None
    product_or_service_area: str | None = None
    region: str | None = None
    approval_status: str | None = None
    reusable_flag: bool | None = None
    sheet_name: str | None = None
    heading_path: tuple[str, ...] = ()
    source_reference: SourceReference | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedSection:
    section_id: str
    title: str
    text: str
    kind: str
    heading_path: tuple[str, ...] = ()
    structured_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ParsedDocument:
    source_file: Path
    file_type: str
    document_type: str
    extracted_at: datetime
    sections: list[ParsedSection] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str
    embedding_text: str
    metadata: ChunkMetadata
    structured_content: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    match_reason: str
