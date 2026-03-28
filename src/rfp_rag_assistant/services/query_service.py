from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rfp_rag_assistant.config import AppSettings
from rfp_rag_assistant.models import RetrievalResult
from rfp_rag_assistant.retrieval import RetrievalService, Retriever


@dataclass(slots=True)
class QueryService:
    retriever: Retriever
    settings: AppSettings

    def query(
        self,
        query: str,
        *,
        top_k: int | None = None,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        service = RetrievalService(retriever=self.retriever)
        effective_top_k = top_k or self.settings.retrieval.default_top_k
        effective_filters = dict(filters or {})
        if self.settings.retrieval.require_approved_answers:
            effective_filters.setdefault("approval_status", "approved")
        return service.retrieve_answers(query, top_k=effective_top_k, filters=effective_filters)
