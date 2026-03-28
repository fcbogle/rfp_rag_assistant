from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rfp_rag_assistant.config import AppSettings, load_config
from rfp_rag_assistant.services.container import AppContainer


@dataclass(slots=True)
class Application:
    settings: AppSettings
    container: AppContainer

    @classmethod
    def build(
        cls,
        *,
        env_file: Path | None = None,
        config_file: Path | None = None,
    ) -> "Application":
        settings = load_config(env_file=env_file, config_file=config_file)
        container = AppContainer.build(settings=settings)
        return cls(settings=settings, container=container)


def build_application(
    *,
    env_file: Path | None = None,
    config_file: Path | None = None,
) -> Application:
    return Application.build(env_file=env_file, config_file=config_file)
