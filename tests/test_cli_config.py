from rfp_rag_assistant.config import (
    AppSettings,
    AzureStorageSettings,
    IngestionSettings,
    LoggingSettings,
)


def test_settings_dataclasses_accept_storage_and_logging() -> None:
    settings = AppSettings(
        azure_storage=AzureStorageSettings(account="acct", key="secret"),
        ingestion=IngestionSettings(chunk_size_tokens=512, overlap_tokens=128),
        logging=LoggingSettings(level="DEBUG", to_file=True),
    )

    assert settings.azure_storage.account == "acct"
    assert settings.ingestion.chunk_size_tokens == 512
    assert settings.logging.to_file is True
