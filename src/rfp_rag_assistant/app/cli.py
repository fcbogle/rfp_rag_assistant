from __future__ import annotations

import argparse
import json
from pathlib import Path

from rfp_rag_assistant.config import AppSettings


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
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = AppSettings.load()

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

    print("rfp_rag_assistant scaffold is installed. Use --print-config to inspect defaults.")


if __name__ == "__main__":
    main()
