from __future__ import annotations

from enum import StrEnum


class PromptMode(StrEnum):
    RETRIEVE_ONLY = "retrieve_only"
    GROUNDED_ANSWER = "grounded_answer"
    DRAFT_GENERATION = "draft_generation"


def build_prompt(mode: PromptMode, query: str) -> str:
    guardrails = (
        "Use only retrieved internal content. Do not invent certifications, "
        "commitments, service levels, or capabilities. Cite sources explicitly."
    )
    if mode is PromptMode.RETRIEVE_ONLY:
        return f"{guardrails}\n\nReturn only relevant retrieved evidence for: {query}"
    if mode is PromptMode.GROUNDED_ANSWER:
        return f"{guardrails}\n\nSynthesize a grounded answer for: {query}"
    return f"{guardrails}\n\nProduce a DRAFT RFP response for: {query}"
