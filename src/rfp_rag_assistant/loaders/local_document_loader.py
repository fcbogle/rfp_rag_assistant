from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import LoadedDocument


@dataclass(slots=True)
class LocalDocumentLoader:
    def load(self, source_file: Path) -> LoadedDocument:
        return LoadedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            payload=source_file,
        )
