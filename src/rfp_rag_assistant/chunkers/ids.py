from __future__ import annotations

import hashlib
from pathlib import Path
import re


def build_chunk_id(source_file: Path, section_id: str, index: int) -> str:
    source_prefix = _slugify(source_file.stem)[:24] or "document"
    digest = hashlib.sha1(f"{source_file.as_posix()}::{section_id}::{index}".encode("utf-8")).hexdigest()[:12]
    return f"{source_prefix}-{digest}-{index}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"
