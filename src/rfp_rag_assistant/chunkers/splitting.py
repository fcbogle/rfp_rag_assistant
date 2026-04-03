from __future__ import annotations

from dataclasses import dataclass
import math
import re


@dataclass(slots=True)
class TextSplitter:
    chunk_size_tokens: int = 300
    overlap_tokens: int = 100

    def split(self, text: str) -> list[str]:
        paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
        if not paragraphs:
            stripped = text.strip()
            paragraphs = [stripped] if stripped else []

        chunks: list[list[str]] = []
        current: list[str] = []
        current_tokens = 0

        for paragraph in paragraphs:
            paragraph_parts = (
                self._split_oversized_paragraph(paragraph)
                if self.estimate_tokens(paragraph) > self.chunk_size_tokens
                else [paragraph]
            )

            for part in paragraph_parts:
                part_tokens = self.estimate_tokens(part)
                if current and current_tokens + part_tokens > self.chunk_size_tokens:
                    chunks.append(current)
                    current = self._tail_overlap(current)
                    current_tokens = self.estimate_tokens("\n\n".join(current))
                current.append(part)
                current_tokens += part_tokens

        if current:
            chunks.append(current)

        return ["\n\n".join(chunk).strip() for chunk in chunks if any(piece.strip() for piece in chunk)]

    def estimate_tokens(self, text: str) -> int:
        words = len(text.split())
        return max(1, math.ceil(words * 1.3))

    def _split_oversized_paragraph(self, paragraph: str) -> list[str]:
        sentences = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", paragraph) if sentence.strip()]
        if len(sentences) <= 1:
            return self._split_by_token_window(paragraph)

        parts: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.estimate_tokens(sentence)
            if sentence_tokens > self.chunk_size_tokens:
                if current:
                    parts.append(" ".join(current).strip())
                    current = []
                    current_tokens = 0
                parts.extend(self._split_by_token_window(sentence))
                continue

            if current and current_tokens + sentence_tokens > self.chunk_size_tokens:
                parts.append(" ".join(current).strip())
                current = []
                current_tokens = 0

            current.append(sentence)
            current_tokens += sentence_tokens

        if current:
            parts.append(" ".join(current).strip())

        return [part for part in parts if part]

    def _split_by_token_window(self, text: str) -> list[str]:
        words = text.split()
        if not words:
            return []

        step = max(1, self.chunk_size_tokens - self.overlap_tokens)
        parts = []
        for start in range(0, len(words), step):
            segment = words[start : start + self.chunk_size_tokens]
            if not segment:
                continue
            parts.append(" ".join(segment))
            if start + self.chunk_size_tokens >= len(words):
                break
        return parts

    def _tail_overlap(self, parts: list[str]) -> list[str]:
        if not parts or self.overlap_tokens <= 0:
            return []

        overlap_parts: list[str] = []
        consumed = 0
        for part in reversed(parts):
            part_tokens = self.estimate_tokens(part)
            overlap_parts.insert(0, part)
            consumed += part_tokens
            if consumed >= self.overlap_tokens:
                break
        return overlap_parts
