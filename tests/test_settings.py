from pathlib import Path

from rfp_rag_assistant.config import AppSettings


def test_settings_loads_from_config_and_env_file(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.toml"
    config_file.write_text(
        '[app]\n'
        'data_dir = "configured-data"\n'
        'index_dir = "configured-index"\n'
        'log_level = "WARNING"\n'
        'default_prompt_mode = "grounded_answer"\n'
        'supported_extensions = [".docx"]\n'
        '\n[chroma]\n'
        'collection = "rfp_history"\n'
        '\n[retrieval]\n'
        'default_top_k = 8\n'
        '\n[ingestion]\n'
        'word_chunk_max_chars = 5000\n'
        'chunk_size_tokens = 256\n'
        '\n[logging]\n'
        'file = "logs/test.log"\n'
    )

    env_file = tmp_path / ".env"
    env_file.write_text(
        "RFP_RAG_LOG_LEVEL=DEBUG\n"
        "RFP_RAG_SUPPORTED_EXTENSIONS=.docx,.xlsx\n"
        "OPENAI_CHAT_MODEL=gpt-5-mini\n"
        "RFP_RAG_DEFAULT_TOP_K=6\n"
        "AZURE_STORAGE_ACCOUNT=blob-account\n"
        "RFP_RAG_BLOB_CONTAINER=rfp-rag-assistant\n"
        "RFP_RAG_BLOB_PREFIX=incoming/\n"
        "RFP_RAG_CHROMA_NAMESPACE=test\n"
        "RFP_RAG_CHUNK_SIZE_TOKENS=512\n"
        "RFP_RAG_OVERLAP_TOKENS=128\n"
        "RFP_RAG_LOG_TO_FILE=true\n"
    )

    settings = AppSettings.load(env_file=env_file, config_file=config_file)

    assert settings.data_dir == Path("configured-data")
    assert settings.index_dir == Path("configured-index")
    assert settings.log_level == "DEBUG"
    assert settings.default_prompt_mode == "grounded_answer"
    assert settings.supported_extensions == (".docx", ".xlsx")
    assert settings.openai.chat_model == "gpt-5-mini"
    assert settings.azure_storage.account == "blob-account"
    assert settings.azure_storage.container == "rfp-rag-assistant"
    assert settings.azure_storage.prefix == "incoming/"
    assert settings.chroma.namespace == "test"
    assert settings.chroma.collection == "rfp_history"
    assert settings.retrieval.default_top_k == 6
    assert settings.ingestion.word_chunk_max_chars == 5000
    assert settings.ingestion.chunk_size_tokens == 512
    assert settings.ingestion.overlap_tokens == 128
    assert settings.logging.level == "DEBUG"
    assert settings.logging.to_file is True
    assert settings.logging.file == "logs/test.log"
