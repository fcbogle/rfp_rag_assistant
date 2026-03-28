from __future__ import annotations

from dataclasses import dataclass

from rfp_rag_assistant.config import AppSettings


@dataclass(slots=True)
class HealthService:
    settings: AppSettings

    def check(self) -> dict[str, bool]:
        return {
            "config_loaded": True,
            "openai_configured": bool(self.settings.openai.api_key or self.settings.azure_openai.api_key),
            "blob_storage_configured": bool(
                self.settings.azure_storage.account and self.settings.azure_storage.key
            ),
            "vector_store_configured": bool(self.settings.chroma.collection),
        }
