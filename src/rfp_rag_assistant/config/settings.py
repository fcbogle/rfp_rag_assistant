from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppSettings:
    data_dir: Path = Path("data")
    index_dir: Path = Path("data/index")
    log_level: str = "INFO"
    supported_extensions: tuple[str, ...] = field(default_factory=lambda: (".docx", ".xlsx"))
