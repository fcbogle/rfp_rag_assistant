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
    settings = AppSettings()

    if args.print_config:
        print(
            json.dumps(
                {
                    "data_dir": str(settings.data_dir),
                    "index_dir": str(settings.index_dir),
                    "log_level": settings.log_level,
                    "supported_extensions": settings.supported_extensions,
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
