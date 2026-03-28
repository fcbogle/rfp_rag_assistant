from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from .settings import AppSettings


class Config(AppSettings):
    @classmethod
    def from_env(
        cls,
        *,
        env_file: Path | None = None,
        config_file: Path | None = None,
    ) -> "Config":
        settings = AppSettings.load(env_file=env_file, config_file=config_file)
        return cls(**{field.name: getattr(settings, field.name) for field in fields(AppSettings)})


def load_config(
    *,
    env_file: Path | None = None,
    config_file: Path | None = None,
) -> AppSettings:
    return AppSettings.load(env_file=env_file, config_file=config_file)
