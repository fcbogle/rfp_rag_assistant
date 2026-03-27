from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(slots=True)
class LoadedDocument:
    source_file: Path
    file_type: str
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)


class Loader(Protocol):
    def load(self, source_file: Path) -> LoadedDocument:
        """Read a source file into a format suitable for parsing."""
