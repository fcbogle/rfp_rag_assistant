from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rfp_rag_assistant.app.main import Application, build_application
from rfp_rag_assistant.api.routes import router as api_router


def create_api_app(
    *,
    env_file: Path | None = None,
    config_file: Path | None = None,
) -> Any:
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _attach_runtime(app, runtime)
    app.include_router(api_router)
    return app


def _attach_runtime(app: Any, runtime: Application) -> None:
    if getattr(app, "state", None) is None:
        app.state = SimpleNamespace()
    app.state.runtime = runtime
    app.state.application = runtime
    app.state.settings = runtime.settings
    app.state.container = runtime.container
