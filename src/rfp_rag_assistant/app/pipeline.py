from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.chunkers import Chunker
from rfp_rag_assistant.loaders import Loader
from rfp_rag_assistant.models import Chunk, ParsedDocument
from rfp_rag_assistant.parsers import Parser


@dataclass(slots=True)
class IngestionPipeline:
    loader: Loader
    parser: Parser
    chunker: Chunker

    def ingest(self, source_file: Path) -> tuple[ParsedDocument, list[Chunk]]:
        loaded = self.loader.load(source_file)
        parsed = self.parser.parse(loaded)
        chunks = self.chunker.chunk(parsed)
        return parsed, chunks
