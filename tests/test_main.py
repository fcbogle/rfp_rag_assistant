from pathlib import Path

from rfp_rag_assistant.app.main import Application, build_application


def test_application_builds_runtime_from_config(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.toml"
    config_file.write_text('[retrieval]\ndefault_top_k = 11\n')

    env_file = tmp_path / ".env"
    env_file.write_text("RFP_RAG_LOG_LEVEL=WARNING\n")

    app = build_application(env_file=env_file, config_file=config_file)

    assert isinstance(app, Application)
    assert app.settings.retrieval.default_top_k == 11
    assert app.container.settings is app.settings
    assert app.container.health_service.check()["config_loaded"] is True
