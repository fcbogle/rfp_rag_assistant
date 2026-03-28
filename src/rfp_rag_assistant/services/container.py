from __future__ import annotations

from dataclasses import dataclass

from rfp_rag_assistant.config import AppSettings
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

    @classmethod
    def build(cls, settings: AppSettings | None = None) -> "AppContainer":
        resolved_settings = settings or AppSettings.load()
        return cls(settings=resolved_settings, retriever=NullRetriever())

    @property
    def query_service(self) -> QueryService:
        return QueryService(retriever=self.retriever, settings=self.settings)

    @property
    def draft_service(self) -> DraftService:
        return DraftService(query_service=self.query_service, settings=self.settings)

    @property
    def health_service(self) -> HealthService:
        return HealthService(settings=self.settings)
