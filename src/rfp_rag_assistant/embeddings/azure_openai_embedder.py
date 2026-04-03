from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
from typing import Any, Callable, Sequence

from rfp_rag_assistant.config import AzureOpenAISettings
from rfp_rag_assistant.models import Chunk


def _build_azure_client(settings: AzureOpenAISettings) -> Any:
    try:
        from openai import AzureOpenAI
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "The 'openai' package is required to use AzureOpenAIEmbedder. "
            "Install project dependencies to enable embeddings."
        ) from exc

    return AzureOpenAI(
        api_key=settings.api_key,
        azure_endpoint=settings.endpoint,
        api_version=settings.api_version,
    )


@dataclass(slots=True)
class AzureOpenAIEmbedder:
    settings: AzureOpenAISettings
    batch_size: int = 32
    normalize: bool = True
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger(__name__))
    client_factory: Callable[[AzureOpenAISettings], Any] | None = None
    model: str = field(init=False)
    embedding_dim: int | None = field(init=False, default=None)
    _client: Any | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.model = (self.settings.embed_deployment or "").strip() or "text-embedding-3-large"
        self.embedding_dim = None
        self._client = None

    def is_configured(self) -> bool:
        return bool(
            (self.settings.api_key or "").strip()
            and (self.settings.endpoint or "").strip()
            and (self.settings.embed_deployment or "").strip()
        )

    def test_connection(self) -> bool:
        if not self.is_configured():
            return False
        try:
            vectors = self.embed_texts(["connection test"])
            return bool(vectors and vectors[0])
        except Exception:
            self.logger.exception("Azure OpenAI embedding connection test failed")
            return False

    def embed(self, chunks: list[Chunk]) -> list[list[float]]:
        texts = [chunk.embedding_text for chunk in chunks if chunk.embedding_text.strip()]
        return self.embed_texts(texts)

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        clean = [text.strip() for text in texts if isinstance(text, str) and text.strip()]
        if not clean:
            return []

        vectors: list[list[float]] = []
        for start in range(0, len(clean), self.batch_size):
            batch = clean[start : start + self.batch_size]
            response = self._client_instance().embeddings.create(model=self.model, input=batch)
            data = getattr(response, "data", None) or []
            if len(data) != len(batch):
                raise ValueError(
                    f"Embedding response size mismatch: inputs={len(batch)} data={len(data)}"
                )
            for item in data:
                vector = list(getattr(item, "embedding", []) or [])
                if not vector:
                    raise ValueError("Embedding API returned an empty vector")
                self._update_and_check_dim(len(vector))
                vectors.append(self._normalize(vector) if self.normalize else vector)

        return vectors

    def _client_instance(self) -> Any:
        if self._client is None:
            factory = self.client_factory or _build_azure_client
            self._client = factory(self.settings)
        return self._client

    def _update_and_check_dim(self, dim: int) -> None:
        if self.embedding_dim is None:
            self.embedding_dim = dim
            return
        if self.embedding_dim != dim:
            raise RuntimeError(
                f"Embedding dimension mismatch for deployment '{self.model}': "
                f"expected {self.embedding_dim}, got {dim}"
            )

    def _normalize(self, vector: list[float]) -> list[float]:
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
