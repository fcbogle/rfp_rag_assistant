from __future__ import annotations

from pathlib import Path


EMBEDDED_PREFIX = "extracted_embedded"
EMBEDDED_FOLDER = "embedded"


def infer_document_type_from_path(source_file: Path) -> str:
    if not source_file.parts:
        raise ValueError(f"Cannot infer document_type from empty source path: {source_file}")
    if source_file.parts[0] == EMBEDDED_PREFIX:
        if len(source_file.parts) < 2:
            raise ValueError(f"Embedded source path is missing classification segment: {source_file}")
        return source_file.parts[1]
    return source_file.parts[0]


def normalize_blob_upload_path(relative_path: Path) -> Path:
    if not relative_path.parts:
        return relative_path
    if relative_path.parts[0] != EMBEDDED_PREFIX:
        return relative_path
    if len(relative_path.parts) < 3:
        raise ValueError(f"Embedded upload path is missing classification or file segments: {relative_path}")
    classification = relative_path.parts[1]
    remainder = relative_path.parts[2:]
    return Path(classification) / EMBEDDED_FOLDER / Path(*remainder)
