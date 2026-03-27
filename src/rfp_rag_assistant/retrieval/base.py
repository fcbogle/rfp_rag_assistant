from __future__ import annotations

from typing import Any, Protocol

from rfp_rag_assistant.models import RetrievalResult


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        """Return relevant chunks for the provided query."""
