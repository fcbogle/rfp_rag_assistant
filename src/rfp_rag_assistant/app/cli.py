from __future__ import annotations

import argparse
import json
from pathlib import Path

from rfp_rag_assistant.app.main import build_application
from rfp_rag_assistant.app.pipeline import IngestionPipeline
from rfp_rag_assistant.chunkers import (
    BackgroundRequirementsChunker,
    ResponseSupportingMaterialChunker,
    TenderDetailsChunker,
)
from rfp_rag_assistant.loaders import LocalDocumentLoader
from rfp_rag_assistant.models import MasterRFPMetadata
from rfp_rag_assistant.parsers import (
    BackgroundRequirementsParser,
    ResponseSupportingMaterialParser,
    TenderDetailsParser,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RFP RAG assistant scaffold CLI")
    parser.add_argument(
        "--print-config",
        action="store_true",
        help="Print the default application configuration as JSON.",
    )
    parser.add_argument(
        "--source-file",
        type=Path,
        help="Optional source file path to validate extension support.",
    )
    parser.add_argument(
        "--preview-background-file",
        type=Path,
        help="Parse and chunk a background_requirements Word document, then print a JSON summary.",
    )
    parser.add_argument(
        "--preview-supporting-material-file",
        type=Path,
        help="Parse and chunk a response_supporting_material Excel workbook, then print a JSON summary.",
    )
    parser.add_argument(
        "--preview-tender-details-file",
        type=Path,
        help="Parse and chunk a tender_details .docx or .xlsx file, then print a JSON summary.",
    )
    parser.add_argument(
        "--ingest-blob-documents",
        action="store_true",
        help="Ingest supported documents from Azure Blob into Chroma collections.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit for blob ingestion runs.",
    )
    parser.add_argument(
        "--issuing-authority",
        type=str,
        help="Optional issuing authority metadata for the ingestion run.",
    )
    parser.add_argument(
        "--customer",
        type=str,
        help="Optional customer metadata for the ingestion run.",
    )
    parser.add_argument(
        "--rfp-id",
        type=str,
        help="Optional RFP identifier metadata for the ingestion run.",
    )
    parser.add_argument(
        "--rfp-title",
        type=str,
        help="Optional RFP title metadata for the ingestion run.",
    )
    parser.add_argument(
        "--upload-local-folder",
        type=Path,
        help="Upload a local classified source folder tree into Azure Blob, preserving relative paths.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing blobs during upload.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    app = build_application()
    settings = app.settings

    if args.print_config:
        print(
            json.dumps(
                {
                    "data_dir": str(settings.data_dir),
                    "index_dir": str(settings.index_dir),
                    "log_level": settings.log_level,
                    "default_prompt_mode": settings.default_prompt_mode,
                    "supported_extensions": settings.supported_extensions,
                    "openai": {
                        "base_url": settings.openai.base_url,
                        "chat_model": settings.openai.chat_model,
                        "reasoning_model": settings.openai.reasoning_model,
                        "responses_debug": settings.openai.responses_debug,
                    },
                    "azure_openai": {
                        "endpoint": settings.azure_openai.endpoint,
                        "api_version": settings.azure_openai.api_version,
                        "chat_deployment": settings.azure_openai.chat_deployment,
                        "embed_deployment": settings.azure_openai.embed_deployment,
                    },
                    "azure_storage": {
                        "account": settings.azure_storage.account,
                        "container": settings.azure_storage.container,
                        "prefix": settings.azure_storage.prefix,
                    },
                    "chroma": {
                        "endpoint": settings.chroma.endpoint,
                        "tenant": settings.chroma.tenant,
                        "database": settings.chroma.database,
                        "collection": settings.chroma.collection,
                    },
                    "retrieval": {
                        "default_top_k": settings.retrieval.default_top_k,
                        "max_context_chars": settings.retrieval.max_context_chars,
                        "keyword_weight": settings.retrieval.keyword_weight,
                        "semantic_weight": settings.retrieval.semantic_weight,
                        "require_approved_answers": settings.retrieval.require_approved_answers,
                    },
                    "ingestion": {
                        "word_chunk_max_chars": settings.ingestion.word_chunk_max_chars,
                        "excel_row_group_size": settings.ingestion.excel_row_group_size,
                        "preserve_tables": settings.ingestion.preserve_tables,
                        "detect_question_answer_blocks": settings.ingestion.detect_question_answer_blocks,
                        "chunk_size_tokens": settings.ingestion.chunk_size_tokens,
                        "overlap_tokens": settings.ingestion.overlap_tokens,
                    },
                    "logging": {
                        "level": settings.logging.level,
                        "to_file": settings.logging.to_file,
                        "file": settings.logging.file,
                        "max_bytes": settings.logging.max_bytes,
                        "backup_count": settings.logging.backup_count,
                    },
                },
                indent=2,
            )
        )
        return

    if args.source_file is not None:
        suffix = args.source_file.suffix.lower()
        if suffix not in settings.supported_extensions:
            raise SystemExit(f"Unsupported source file type: {suffix}")
        print(f"Accepted source file: {args.source_file}")
        return

    if args.upload_local_folder is not None:
        source_root = args.upload_local_folder
        if not source_root.exists() or not source_root.is_dir():
            raise SystemExit(f"Upload source folder does not exist or is not a directory: {source_root}")

        uploaded: list[dict[str, str]] = []
        skipped = 0
        for local_path in sorted(path for path in source_root.rglob("*") if path.is_file()):
            relative_path = local_path.relative_to(source_root)
            if relative_path.parts and relative_path.parts[0].startswith("."):
                skipped += 1
                continue
            blob_name = app.container.blob_service.upload_file_to_blob(
                settings.azure_storage.container,
                local_path,
                relative_to=source_root,
                overwrite=args.overwrite,
            )
            uploaded.append(
                {
                    "local_path": str(local_path),
                    "blob_name": blob_name,
                }
            )

        print(
            json.dumps(
                {
                    "container_name": settings.azure_storage.container,
                    "uploaded_count": len(uploaded),
                    "skipped_count": skipped,
                    "overwrite": args.overwrite,
                    "files": uploaded[:50],
                },
                indent=2,
            )
        )
        return

    if args.ingest_blob_documents:
        master_metadata = None
        if any([args.issuing_authority, args.customer, args.rfp_id, args.rfp_title]):
            master_metadata = MasterRFPMetadata(
                issuing_authority=args.issuing_authority,
                customer=args.customer,
                rfp_id=args.rfp_id,
                rfp_title=args.rfp_title,
            )
        app.container.ingestion_service.master_metadata = master_metadata
        summary = app.container.ingestion_service.ingest_blob_documents(limit=args.limit)
        print(
            json.dumps(
                {
                    "document_count": summary.document_count,
                    "chunk_count": summary.chunk_count,
                    "indexing": {
                        "total_chunks": summary.indexing.total_chunks,
                        "collections": [
                            {
                                "document_type": item.document_type,
                                "collection_name": item.collection_name,
                                "chunk_count": item.chunk_count,
                            }
                            for item in summary.indexing.collections
                        ],
                    },
                    "documents": [
                        {
                            "source_file": str(item.source_file),
                            "document_type": item.document_type,
                            "section_count": item.section_count,
                            "chunk_count": item.chunk_count,
                        }
                        for item in summary.documents
                    ],
                    "master_metadata": {
                        "issuing_authority": master_metadata.issuing_authority if master_metadata else None,
                        "customer": master_metadata.customer if master_metadata else None,
                        "rfp_id": master_metadata.rfp_id if master_metadata else None,
                        "rfp_title": master_metadata.rfp_title if master_metadata else None,
                    },
                },
                indent=2,
            )
        )
        return

    if args.preview_background_file is not None:
        source_file = args.preview_background_file
        suffix = source_file.suffix.lower()
        if suffix != ".docx":
            raise SystemExit("Background requirements preview currently supports .docx only.")

        pipeline = IngestionPipeline(
            loader=LocalDocumentLoader(),
            parser=BackgroundRequirementsParser(),
            chunker=BackgroundRequirementsChunker(
                chunk_size_tokens=settings.ingestion.chunk_size_tokens,
                overlap_tokens=settings.ingestion.overlap_tokens,
            ),
        )
        parsed, chunks = pipeline.ingest(source_file)
        print(
            json.dumps(
                {
                    "source_file": str(parsed.source_file),
                    "document_type": parsed.document_type,
                    "section_count": len(parsed.sections),
                    "chunk_count": len(chunks),
                    "sections": [
                        {
                            "section_id": section.section_id,
                            "title": section.title,
                            "heading_path": list(section.heading_path),
                            "text_preview": section.text[:160],
                        }
                        for section in parsed.sections[:10]
                    ],
                    "chunks": [
                        {
                            "chunk_id": chunk.chunk_id,
                            "chunk_type": chunk.metadata.chunk_type,
                            "heading_path": list(chunk.metadata.heading_path),
                            "chunk_index": chunk.metadata.extra.get("chunk_index"),
                            "chunk_total": chunk.metadata.extra.get("chunk_total"),
                            "text_preview": chunk.text[:200],
                        }
                        for chunk in chunks[:10]
                    ],
                },
                indent=2,
            )
        )
        return

    if args.preview_supporting_material_file is not None:
        source_file = args.preview_supporting_material_file
        suffix = source_file.suffix.lower()
        if suffix not in {".xlsx", ".pdf"}:
            raise SystemExit("Supporting material preview currently supports .xlsx and .pdf only.")

        pipeline = IngestionPipeline(
            loader=LocalDocumentLoader(),
            parser=ResponseSupportingMaterialParser(),
            chunker=ResponseSupportingMaterialChunker(
                chunk_size_tokens=settings.ingestion.chunk_size_tokens,
                overlap_tokens=settings.ingestion.overlap_tokens,
            ),
        )
        parsed, chunks = pipeline.ingest(source_file)
        print(
            json.dumps(
                {
                    "source_file": str(parsed.source_file),
                    "document_type": parsed.document_type,
                    "section_count": len(parsed.sections),
                    "chunk_count": len(chunks),
                    "sections": [
                        {
                            "section_id": section.section_id,
                            "title": section.title,
                            "kind": section.kind,
                            "heading_path": list(section.heading_path),
                            "sheet_name": section.structured_data.get("sheet_name"),
                            "row_index": section.structured_data.get("row_index"),
                            "text_preview": section.text[:160],
                        }
                        for section in parsed.sections[:10]
                    ],
                    "chunks": [
                        {
                            "chunk_id": chunk.chunk_id,
                            "chunk_type": chunk.metadata.chunk_type,
                            "sheet_name": chunk.metadata.sheet_name,
                            "heading_path": list(chunk.metadata.heading_path),
                            "row_index": chunk.metadata.extra.get("row_index"),
                            "chunk_index": chunk.metadata.extra.get("chunk_index"),
                            "chunk_total": chunk.metadata.extra.get("chunk_total"),
                            "text_preview": chunk.text[:200],
                        }
                        for chunk in chunks[:10]
                    ],
                },
                indent=2,
            )
        )
        return

    if args.preview_tender_details_file is not None:
        source_file = args.preview_tender_details_file
        suffix = source_file.suffix.lower()
        if suffix not in {".docx", ".xlsx", ".pdf"}:
            raise SystemExit("Tender details preview currently supports .docx, .xlsx and .pdf only.")

        pipeline = IngestionPipeline(
            loader=LocalDocumentLoader(),
            parser=TenderDetailsParser(),
            chunker=TenderDetailsChunker(
                chunk_size_tokens=settings.ingestion.chunk_size_tokens,
                overlap_tokens=settings.ingestion.overlap_tokens,
            ),
        )
        parsed, chunks = pipeline.ingest(source_file)
        print(
            json.dumps(
                {
                    "source_file": str(parsed.source_file),
                    "document_type": parsed.document_type,
                    "subtype": parsed.metadata.get("subtype"),
                    "section_count": len(parsed.sections),
                    "chunk_count": len(chunks),
                    "sections": [
                        {
                            "section_id": section.section_id,
                            "title": section.title,
                            "kind": section.kind,
                            "heading_path": list(section.heading_path),
                            "sheet_name": section.structured_data.get("sheet_name"),
                            "row_index": section.structured_data.get("row_index"),
                            "text_preview": section.text[:160],
                        }
                        for section in parsed.sections[:10]
                    ],
                    "chunks": [
                        {
                            "chunk_id": chunk.chunk_id,
                            "chunk_type": chunk.metadata.chunk_type,
                            "sheet_name": chunk.metadata.sheet_name,
                            "heading_path": list(chunk.metadata.heading_path),
                            "row_index": chunk.metadata.extra.get("row_index"),
                            "chunk_index": chunk.metadata.extra.get("chunk_index"),
                            "chunk_total": chunk.metadata.extra.get("chunk_total"),
                            "text_preview": chunk.text[:200],
                        }
                        for chunk in chunks[:10]
                    ],
                },
                indent=2,
            )
        )
        return

    print("rfp_rag_assistant scaffold is installed. Use --print-config to inspect defaults.")


if __name__ == "__main__":
    main()
