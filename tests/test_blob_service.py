from dataclasses import dataclass, field
from pathlib import Path

from rfp_rag_assistant.config.settings import AppSettings, AzureStorageSettings
from rfp_rag_assistant.services.blob_service import BlobService


def test_blob_service_reports_configuration_and_builds_blob_paths() -> None:
    settings = AppSettings(azure_storage=AzureStorageSettings(account="acct", key="secret"))
    service = BlobService(settings=settings)

    assert service.is_configured() is True
    assert service.blob_path("rfp", "incoming", "example.docx") == "rfp/incoming/example.docx"
    assert "AccountName=acct" in service.connection_string()


def test_blob_service_requires_storage_settings() -> None:
    service = BlobService(settings=AppSettings())

    assert service.is_configured() is False


@dataclass
class FakeDownload:
    payload: bytes

    def readall(self) -> bytes:
        return self.payload


@dataclass
class FakeBlobClient:
    payload: bytes

    def download_blob(self) -> FakeDownload:
        return FakeDownload(self.payload)


@dataclass
class FakeBlob:
    name: str


@dataclass
class FakeContainerClient:
    uploaded: list[dict] = field(default_factory=list)

    def exists(self) -> bool:
        return True

    def list_blobs(self, name_starts_with: str = "") -> list[FakeBlob]:
        return [FakeBlob(name=f"{name_starts_with}one.docx"), FakeBlob(name=f"{name_starts_with}two.xlsx")]

    def get_blob_client(self, blob_name: str) -> FakeBlobClient:
        return FakeBlobClient(payload=f"payload:{blob_name}".encode())

    def upload_blob(
        self,
        *,
        name: str,
        data: bytes,
        overwrite: bool,
        metadata: dict[str, str] | None = None,
        content_type: str | None = None,
    ) -> None:
        self.uploaded.append(
            {
                "name": name,
                "data": data,
                "overwrite": overwrite,
                "metadata": metadata,
                "content_type": content_type,
            }
        )


@dataclass
class FakeBlobServiceClient:
    container: FakeContainerClient

    def get_container_client(self, container_name: str) -> FakeContainerClient:
        return self.container


def test_blob_service_supports_basic_client_operations() -> None:
    fake_container = FakeContainerClient()
    fake_client = FakeBlobServiceClient(container=fake_container)
    settings = AppSettings(azure_storage=AzureStorageSettings(account="acct", key="secret"))
    service = BlobService(settings=settings, client_factory=lambda _: fake_client)

    assert service.container_exists("rfp-rag-assistant") is True
    assert service.list_blob_names("rfp-rag-assistant", prefix="incoming/") == [
        "incoming/one.docx",
        "incoming/two.xlsx",
    ]
    assert service.download_blob_bytes("rfp-rag-assistant", "incoming/example.docx") == (
        b"payload:incoming/example.docx"
    )

    service.upload_blob_bytes(
        "rfp-rag-assistant",
        "incoming/example.docx",
        b"example",
        overwrite=True,
        metadata={"document_type": "rfp"},
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    assert fake_container.uploaded == [
        {
            "name": "incoming/example.docx",
            "data": b"example",
            "overwrite": True,
            "metadata": {"document_type": "rfp"},
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
    ]


def test_blob_service_upload_file_to_blob_uses_local_annex_file() -> None:
    fake_container = FakeContainerClient()
    fake_client = FakeBlobServiceClient(container=fake_container)
    settings = AppSettings(azure_storage=AzureStorageSettings(account="acct", key="secret"))
    service = BlobService(settings=settings, client_factory=lambda _: fake_client)
    annex_path = Path(
        "/Users/frankbogle/Documents/RFP/Annex A - East Sussex Specialist Static Postural Seating for Adults.docx"
    )

    blob_name = service.upload_file_to_blob(
        "rfp-rag-assistant",
        annex_path,
        blob_name="incoming/Annex A - East Sussex Specialist Static Postural Seating for Adults.docx",
        overwrite=True,
    )

    assert blob_name == "incoming/Annex A - East Sussex Specialist Static Postural Seating for Adults.docx"
    assert fake_container.uploaded[0]["name"] == blob_name
    assert fake_container.uploaded[0]["overwrite"] is True
    assert fake_container.uploaded[0]["data"] == annex_path.read_bytes()
    assert fake_container.uploaded[0]["content_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_blob_service_download_blob_to_file_writes_local_file(tmp_path: Path) -> None:
    fake_container = FakeContainerClient()
    fake_client = FakeBlobServiceClient(container=fake_container)
    settings = AppSettings(azure_storage=AzureStorageSettings(account="acct", key="secret"))
    service = BlobService(settings=settings, client_factory=lambda _: fake_client)
    target_path = tmp_path / "downloads" / "Annex A.docx"

    written_path = service.download_blob_to_file(
        "rfp-rag-assistant",
        "incoming/Annex A.docx",
        target_path,
    )

    assert written_path == target_path
    assert target_path.read_bytes() == b"payload:incoming/Annex A.docx"
