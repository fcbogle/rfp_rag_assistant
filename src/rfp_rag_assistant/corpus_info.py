from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from rfp_rag_assistant.config import AppSettings
from rfp_rag_assistant.embeddings.chroma_indexer import ChromaIndexer


@dataclass(frozen=True, slots=True)
class ClassificationInfo:
    document_type: str
    title: str
    purpose: str
    rationale: str
    primary_value: str


CLASSIFICATION_INFO: tuple[ClassificationInfo, ...] = (
    ClassificationInfo(
        document_type="combined_qa",
        title="Combined Q&A",
        purpose="Historic supplier responses where tender questions and answer content are strongly paired.",
        rationale="This corpus is the closest match to future bid writing because it contains reusable prior answers tied to specific question contexts.",
        primary_value="Best source for direct answer reuse and response phrasing.",
    ),
    ClassificationInfo(
        document_type="response_supporting_material",
        title="Response Supporting Material",
        purpose="Supplier-authored supporting statements, appendices, plans, reports, and policy material submitted alongside prior bids.",
        rationale="This corpus provides the evidence, delivery detail, governance wording, and capability support that sits behind direct answers.",
        primary_value="Best source for supporting evidence and grounding detail.",
    ),
    ClassificationInfo(
        document_type="background_requirements",
        title="Background Requirements",
        purpose="Buyer-issued service context, specifications, contract material, financial templates, and requirement documents.",
        rationale="This corpus defines the environment, constraints, and expected obligations that future answers need to align with.",
        primary_value="Best source for service context and requirement grounding.",
    ),
    ClassificationInfo(
        document_type="tender_details",
        title="Tender Details",
        purpose="Buyer-issued procurement instructions, evaluation methodology, administrative rules, and tender process documents.",
        rationale="This corpus explains how the procurement is run and how responses will be judged, but it is usually less useful for direct answer text reuse.",
        primary_value="Best source for procurement process and submission rules.",
    ),
    ClassificationInfo(
        document_type="external_reference",
        title="External References",
        purpose="Reviewed external URLs cited by the buyer or supplier that may provide authoritative guidance or context.",
        rationale="This corpus captures relevant public guidance separately from internal material so it can be used deliberately and ranked appropriately.",
        primary_value="Best source for customer-cited external guidance and supporting public references.",
    ),
)


def build_corpus_info(settings: AppSettings, chroma_indexer: ChromaIndexer) -> dict[str, Any]:
    collection_targets = [
        {
            "document_type": item.document_type,
            "collection_name": chroma_indexer.collection_name_for(item.document_type),
        }
        for item in CLASSIFICATION_INFO
    ]
    return {
        "blob": {
            "account": settings.azure_storage.account or None,
            "container": settings.azure_storage.container,
            "prefix": settings.azure_storage.prefix,
            "region": settings.azure_storage.region or None,
            "supported_extensions": list(settings.supported_extensions),
        },
        "chroma": {
            "endpoint": settings.chroma.endpoint or None,
            "database": settings.chroma.database or None,
            "tenant": settings.chroma.tenant or None,
            "region": settings.chroma.region or None,
            "namespace": settings.chroma.namespace,
            "collection_base": settings.chroma.collection,
            "target_collections": collection_targets,
        },
        "classifications": [asdict(item) for item in CLASSIFICATION_INFO],
    }
