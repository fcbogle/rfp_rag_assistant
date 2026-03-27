from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class RetrievalEvaluation:
    query: str
    expected_sources: list[str]
    observed_sources: list[str]

    @property
    def recall(self) -> float:
        if not self.expected_sources:
            return 1.0
        expected = set(self.expected_sources)
        observed = set(self.observed_sources)
        return len(expected & observed) / len(expected)
