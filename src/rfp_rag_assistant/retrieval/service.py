from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rfp_rag_assistant.models import RetrievalResult
from rfp_rag_assistant.retrieval.base import Retriever


@dataclass(slots=True)
class RetrievalService:
    retriever: Retriever

    def retrieve_answers(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        return self.retriever.retrieve(query, top_k=top_k, filters=filters)
