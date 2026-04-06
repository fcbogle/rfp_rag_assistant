from pathlib import Path

from rfp_rag_assistant.config.settings import (
    AppSettings,
    AzureStorageSettings,
    ChromaSettings,
    RetrievalSettings,
)
from rfp_rag_assistant.services.container import AppContainer


def test_app_container_builds_service_graph() -> None:
    settings = AppSettings(
        azure_storage=AzureStorageSettings(
            account="acct",
            key="secret",
            container="rfp-rag-assistant",
            prefix="incoming/",
        ),
        chroma=ChromaSettings(collection="rfp_answers"),
        retrieval=RetrievalSettings(default_top_k=7),
    )

    container = AppContainer.build(settings)

    assert container.health_service.check()["config_loaded"] is True
    assert container.health_service.check()["blob_storage_configured"] is True
    assert container.blob_service.is_configured() is True
    assert container.blob_document_loader.container_name == "rfp-rag-assistant"
    assert container.blob_document_loader.prefix == "incoming/"
    assert set(container.parsers) == {
        "combined_qa",
        "background_requirements",
        "response_supporting_material",
        "tender_details",
        "external_reference",
    }
    assert set(container.chunkers) == {
        "combined_qa",
        "background_requirements",
        "response_supporting_material",
        "tender_details",
        "external_reference",
    }
    assert container.chroma_indexer.embedder is container.embedder
    assert container.ingestion_service.blob_document_loader is container.blob_document_loader
    assert container.ingestion_service.parsers is container.parsers
    assert container.ingestion_service.chunkers is container.chunkers
    assert container.ingestion_service.chroma_indexer is container.chroma_indexer
    assert container.reconciliation_service.blob_document_loader is container.blob_document_loader
    assert container.reconciliation_service.blob_service is container.blob_service
    assert container.reconciliation_service.chroma_indexer is container.chroma_indexer
    assert container.query_service.settings.retrieval.default_top_k == 7
    assert container.draft_service.query_service is container.query_service


def test_app_container_uses_loaded_settings_once(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.toml"
    config_file.write_text('[retrieval]\ndefault_top_k = 9\n')

    env_file = tmp_path / ".env"
    env_file.write_text(
        "RFP_RAG_LOG_LEVEL=DEBUG\n"
        "RFP_RAG_BLOB_CONTAINER=rfp-rag-assistant\n"
        "RFP_RAG_BLOB_PREFIX=incoming/test-rfp/\n"
    )

    container = AppContainer.build(env_file=env_file, config_file=config_file)

    assert container.settings.retrieval.default_top_k == 9
    assert container.settings.log_level == "DEBUG"
    assert container.blob_document_loader.prefix == "incoming/test-rfp/"
