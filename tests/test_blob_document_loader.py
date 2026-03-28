from pathlib import Path

from rfp_rag_assistant.config.settings import AppSettings, AzureStorageSettings
from rfp_rag_assistant.loaders.blob_document_loader import BlobDocumentLoader
from rfp_rag_assistant.services.blob_service import BlobService


class StubBlobService(BlobService):
    def __init__(self) -> None:
        super().__init__(settings=AppSettings(azure_storage=AzureStorageSettings(account="acct", key="secret")))

    def list_blob_names(self, container_name: str, *, prefix: str = "") -> list[str]:
        return [
            f"{prefix}Annex A.docx",
            f"{prefix}pricing.xlsx",
            f"{prefix}notes.txt",
        ]

    def download_blob_bytes(self, container_name: str, blob_name: str) -> bytes:
        return f"downloaded:{container_name}:{blob_name}".encode()


def test_blob_document_loader_lists_supported_documents() -> None:
    loader = BlobDocumentLoader(
        blob_service=StubBlobService(),
        container_name="rfp-rag-assistant",
        prefix="incoming/",
    )

    assert loader.list_documents() == [
        Path("incoming/Annex A.docx"),
        Path("incoming/pricing.xlsx"),
    ]


def test_blob_document_loader_loads_blob_into_loaded_document() -> None:
    loader = BlobDocumentLoader(
        blob_service=StubBlobService(),
        container_name="rfp-rag-assistant",
        prefix="incoming/",
    )

    loaded = loader.load(Path("incoming/Annex A.docx"))

    assert loaded.source_file == Path("incoming/Annex A.docx")
    assert loaded.file_type == "docx"
    assert loaded.payload == b"downloaded:rfp-rag-assistant:incoming/Annex A.docx"
    assert loaded.metadata["container_name"] == "rfp-rag-assistant"
