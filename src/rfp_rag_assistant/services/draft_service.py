from __future__ import annotations

from dataclasses import dataclass

from rfp_rag_assistant.config import AppSettings
from rfp_rag_assistant.prompts import PromptMode, build_prompt
from rfp_rag_assistant.services.query_service import QueryService


@dataclass(slots=True)
class DraftService:
    query_service: QueryService
    settings: AppSettings

    def build_grounded_prompt(self, query: str, *, mode: PromptMode | None = None) -> str:
        selected_mode = mode or PromptMode(self.settings.default_prompt_mode)
        results = self.query_service.query(query)
        evidence_block = "\n".join(
            f"- [{result.chunk.metadata.chunk_type}] {result.chunk.text}"
            for result in results
        ) or "- No evidence retrieved."
        prompt = build_prompt(selected_mode, query)
        return f"{prompt}\n\nRetrieved evidence:\n{evidence_block}"
