from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rfp_rag_assistant.app.main import Application, build_application


def create_api_app(
    *,
    env_file: Path | None = None,
    config_file: Path | None = None,
) -> Any:
    try:
        from fastapi import FastAPI
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on local package install
        raise RuntimeError(
            "The 'fastapi' package is required to create the API application. "
            "Install project dependencies to enable the web service."
        ) from exc

    runtime = build_application(env_file=env_file, config_file=config_file)
    app = FastAPI(
        title="RFP RAG Assistant API",
        version="0.1.0",
    )
    _attach_runtime(app, runtime)
    return app


def _attach_runtime(app: Any, runtime: Application) -> None:
    if getattr(app, "state", None) is None:
        app.state = SimpleNamespace()
    app.state.runtime = runtime
    app.state.application = runtime
    app.state.settings = runtime.settings
    app.state.container = runtime.container
