from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rfp_rag_assistant.config import AppSettings, load_config
from rfp_rag_assistant.models import RetrievalResult
from rfp_rag_assistant.retrieval import Retriever
from rfp_rag_assistant.services.draft_service import DraftService
from rfp_rag_assistant.services.health_service import HealthService
from rfp_rag_assistant.services.query_service import QueryService


class NullRetriever:
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        return []


@dataclass(slots=True)
class AppContainer:
    settings: AppSettings
    retriever: Retriever
    query_service: QueryService = field(init=False)
    draft_service: DraftService = field(init=False)
    health_service: HealthService = field(init=False)

    def __post_init__(self) -> None:
        self.query_service = QueryService(retriever=self.retriever, settings=self.settings)
        self.draft_service = DraftService(query_service=self.query_service, settings=self.settings)
        self.health_service = HealthService(settings=self.settings)

    @classmethod
    def build(
        cls,
        settings: AppSettings | None = None,
        *,
        retriever: Retriever | None = None,
        env_file: Path | None = None,
        config_file: Path | None = None,
    ) -> "AppContainer":
        resolved_settings = settings or load_config(env_file=env_file, config_file=config_file)
        resolved_retriever = retriever or NullRetriever()
        return cls(settings=resolved_settings, retriever=resolved_retriever)
