from __future__ import annotations

from pathlib import Path
from types import ModuleType, SimpleNamespace
import sys

import pytest

from rfp_rag_assistant.api import create_api_app
from rfp_rag_assistant.app.main import Application


class _FakeFastAPI:
    def __init__(self, *, title: str, version: str) -> None:
        self.title = title
        self.version = version
        self.state = SimpleNamespace()
        self.routers = []

    def include_router(self, router) -> None:
        self.routers.append(router)


def test_create_api_app_attaches_runtime(monkeypatch, tmp_path: Path) -> None:
    fake_fastapi_module = ModuleType("fastapi")
    fake_fastapi_module.FastAPI = _FakeFastAPI
    monkeypatch.setitem(sys.modules, "fastapi", fake_fastapi_module)

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_file = config_dir / "app.toml"
    config_file.write_text('[retrieval]\ndefault_top_k = 11\n')
    env_file = tmp_path / ".env"
    env_file.write_text("RFP_RAG_LOG_LEVEL=WARNING\n")

    app = create_api_app(env_file=env_file, config_file=config_file)

    assert app.title == "RFP RAG Assistant API"
    assert app.version == "0.1.0"
    assert isinstance(app.state.runtime, Application)
    assert app.state.application is app.state.runtime
    assert app.state.settings is app.state.runtime.settings
    assert app.state.container is app.state.runtime.container
    assert app.state.settings.retrieval.default_top_k == 11
    assert app.routers


def test_create_api_app_requires_fastapi(monkeypatch) -> None:
    monkeypatch.delitem(sys.modules, "fastapi", raising=False)

    real_import = __import__

    def _raising_import(name, *args, **kwargs):
        if name == "fastapi":
            raise ModuleNotFoundError("No module named 'fastapi'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", _raising_import)

    with pytest.raises(RuntimeError, match="The 'fastapi' package is required"):
        create_api_app()
