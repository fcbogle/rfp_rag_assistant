from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rfp_rag_assistant.loaders.base import LoadedDocument

if TYPE_CHECKING:
    from rfp_rag_assistant.services.blob_service import BlobService


@dataclass(slots=True)
class BlobDocumentLoader:
    blob_service: "BlobService"
    container_name: str
    prefix: str = ""
    supported_extensions: tuple[str, ...] = (".docx", ".xlsx")

    def list_documents(self) -> list[Path]:
        blob_names = self.blob_service.list_blob_names(self.container_name, prefix=self.prefix)
        supported = []
        for blob_name in blob_names:
            path = Path(blob_name)
            if path.suffix.lower() in self.supported_extensions:
                supported.append(path)
        return supported

    def load(self, source_file: Path) -> LoadedDocument:
        blob_name = str(source_file).replace("\\", "/")
        payload = self.blob_service.download_blob_bytes(self.container_name, blob_name)
        return LoadedDocument(
            source_file=source_file,
            file_type=source_file.suffix.lstrip(".").lower(),
            payload=payload,
            metadata={
                "container_name": self.container_name,
                "blob_name": blob_name,
                "prefix": self.prefix,
            },
        )
