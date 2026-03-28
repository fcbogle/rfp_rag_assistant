from pathlib import Path

from rfp_rag_assistant.config import AppSettings, Config, load_config


def test_config_wrapper_loads_settings(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.toml"
    config_file.write_text('[app]\nlog_level = "WARNING"\n')

    env_file = tmp_path / ".env"
    env_file.write_text("RFP_RAG_LOG_LEVEL=DEBUG\n")

    loaded = load_config(env_file=env_file, config_file=config_file)
    wrapped = Config.from_env(env_file=env_file, config_file=config_file)

    assert isinstance(loaded, AppSettings)
    assert isinstance(wrapped, Config)
    assert loaded.log_level == "DEBUG"
    assert wrapped.log_level == "DEBUG"
