from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values


def _read_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    with path.open("rb") as handle:
        return tomllib.load(handle)


def _as_bool(value: str | bool | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value

    normalised = str(value).strip().lower()
    if normalised in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if normalised in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _as_int(value: str | int | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)


@dataclass(slots=True, frozen=True)
class OpenAISettings:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    chat_model: str = "gpt-5"
    reasoning_model: str = "gpt-5"
    responses_debug: bool = False


@dataclass(slots=True, frozen=True)
class AzureOpenAISettings:
    api_key: str = ""
    endpoint: str = ""
    api_version: str = "2024-10-21"
    chat_deployment: str = ""
    embed_deployment: str = ""


@dataclass(slots=True, frozen=True)
class ChromaSettings:
    endpoint: str = ""
    api_key: str = ""
    tenant: str = ""
    database: str = ""
    collection: str = "rfp_answers"


@dataclass(slots=True, frozen=True)
class RetrievalSettings:
    default_top_k: int = 5
    max_context_chars: int = 12000
    keyword_weight: float = 0.35
    semantic_weight: float = 0.65
    require_approved_answers: bool = False


@dataclass(slots=True, frozen=True)
class IngestionSettings:
    word_chunk_max_chars: int = 4000
    excel_row_group_size: int = 1
    preserve_tables: bool = True
    detect_question_answer_blocks: bool = True


@dataclass(slots=True)
class AppSettings:
    data_dir: Path = Path("data")
    index_dir: Path = Path("data/index")
    log_level: str = "INFO"
    default_prompt_mode: str = "retrieve_only"
    supported_extensions: tuple[str, ...] = field(default_factory=lambda: (".docx", ".xlsx"))
    openai: OpenAISettings = field(default_factory=OpenAISettings)
    azure_openai: AzureOpenAISettings = field(default_factory=AzureOpenAISettings)
    chroma: ChromaSettings = field(default_factory=ChromaSettings)
    retrieval: RetrievalSettings = field(default_factory=RetrievalSettings)
    ingestion: IngestionSettings = field(default_factory=IngestionSettings)

    @classmethod
    def load(
        cls,
        *,
        env_file: Path | None = None,
        config_file: Path | None = None,
    ) -> "AppSettings":
        env_path = env_file or Path(".env")
        config_path = config_file or Path("config/app.toml")

        config_values = _read_config_file(config_path)
        env_values = _read_dotenv(env_path)

        app_config = config_values.get("app", {})
        openai_config = config_values.get("openai", {})
        azure_openai_config = config_values.get("azure_openai", {})
        chroma_config = config_values.get("chroma", {})
        retrieval_config = config_values.get("retrieval", {})
        ingestion_config = config_values.get("ingestion", {})
        source_values = {
            "data_dir": env_values.get("RFP_RAG_DATA_DIR", app_config.get("data_dir", "data")),
            "index_dir": env_values.get("RFP_RAG_INDEX_DIR", app_config.get("index_dir", "data/index")),
            "log_level": env_values.get("RFP_RAG_LOG_LEVEL", app_config.get("log_level", "INFO")),
            "default_prompt_mode": env_values.get(
                "RFP_RAG_DEFAULT_PROMPT_MODE",
                app_config.get("default_prompt_mode", "retrieve_only"),
            ),
            "supported_extensions": env_values.get(
                "RFP_RAG_SUPPORTED_EXTENSIONS",
                ",".join(app_config.get("supported_extensions", [".docx", ".xlsx"])),
            ),
        }

        source_values["data_dir"] = os.getenv("RFP_RAG_DATA_DIR", source_values["data_dir"])
        source_values["index_dir"] = os.getenv("RFP_RAG_INDEX_DIR", source_values["index_dir"])
        source_values["log_level"] = os.getenv("RFP_RAG_LOG_LEVEL", source_values["log_level"])
        source_values["default_prompt_mode"] = os.getenv(
            "RFP_RAG_DEFAULT_PROMPT_MODE",
            source_values["default_prompt_mode"],
        )
        source_values["supported_extensions"] = os.getenv(
            "RFP_RAG_SUPPORTED_EXTENSIONS",
            source_values["supported_extensions"],
        )

        supported_extensions = tuple(
            item.strip()
            for item in str(source_values["supported_extensions"]).split(",")
            if item.strip()
        )

        return cls(
            data_dir=Path(str(source_values["data_dir"])),
            index_dir=Path(str(source_values["index_dir"])),
            log_level=str(source_values["log_level"]),
            default_prompt_mode=str(source_values["default_prompt_mode"]),
            supported_extensions=supported_extensions,
            openai=OpenAISettings(
                base_url=os.getenv(
                    "OPENAI_BASE_URL",
                    env_values.get("OPENAI_BASE_URL", openai_config.get("base_url", "https://api.openai.com/v1")),
                ),
                api_key=os.getenv(
                    "OPENAI_API_KEY",
                    env_values.get("OPENAI_API_KEY", openai_config.get("api_key", "")),
                ),
                chat_model=os.getenv(
                    "OPENAI_CHAT_MODEL",
                    env_values.get("OPENAI_CHAT_MODEL", openai_config.get("chat_model", "gpt-5")),
                ),
                reasoning_model=os.getenv(
                    "OPENAI_REASONING_MODEL",
                    env_values.get("OPENAI_REASONING_MODEL", openai_config.get("reasoning_model", "gpt-5")),
                ),
                responses_debug=_as_bool(
                    os.getenv(
                        "OPENAI_RESPONSES_DEBUG",
                        env_values.get("OPENAI_RESPONSES_DEBUG", openai_config.get("responses_debug", False)),
                    ),
                    default=False,
                ),
            ),
            azure_openai=AzureOpenAISettings(
                api_key=os.getenv(
                    "AZURE_OPENAI_API_KEY",
                    env_values.get("AZURE_OPENAI_API_KEY", azure_openai_config.get("api_key", "")),
                ),
                endpoint=os.getenv(
                    "AZURE_OPENAI_ENDPOINT",
                    env_values.get("AZURE_OPENAI_ENDPOINT", azure_openai_config.get("endpoint", "")),
                ),
                api_version=os.getenv(
                    "AZURE_OPENAI_API_VERSION",
                    env_values.get("AZURE_OPENAI_API_VERSION", azure_openai_config.get("api_version", "2024-10-21")),
                ),
                chat_deployment=os.getenv(
                    "AZURE_OPENAI_CHAT_DEPLOYMENT",
                    env_values.get("AZURE_OPENAI_CHAT_DEPLOYMENT", azure_openai_config.get("chat_deployment", "")),
                ),
                embed_deployment=os.getenv(
                    "AZURE_OPENAI_EMBED_DEPLOYMENT",
                    env_values.get("AZURE_OPENAI_EMBED_DEPLOYMENT", azure_openai_config.get("embed_deployment", "")),
                ),
            ),
            chroma=ChromaSettings(
                endpoint=os.getenv(
                    "CHROMA_ENDPOINT",
                    env_values.get("CHROMA_ENDPOINT", chroma_config.get("endpoint", "")),
                ),
                api_key=os.getenv(
                    "CHROMA_API_KEY",
                    env_values.get("CHROMA_API_KEY", chroma_config.get("api_key", "")),
                ),
                tenant=os.getenv(
                    "CHROMA_TENANT",
                    env_values.get("CHROMA_TENANT", chroma_config.get("tenant", "")),
                ),
                database=os.getenv(
                    "CHROMA_DATABASE",
                    env_values.get("CHROMA_DATABASE", chroma_config.get("database", "")),
                ),
                collection=os.getenv(
                    "RFP_RAG_VECTOR_COLLECTION",
                    env_values.get("RFP_RAG_VECTOR_COLLECTION", chroma_config.get("collection", "rfp_answers")),
                ),
            ),
            retrieval=RetrievalSettings(
                default_top_k=_as_int(
                    os.getenv(
                        "RFP_RAG_DEFAULT_TOP_K",
                        env_values.get("RFP_RAG_DEFAULT_TOP_K", retrieval_config.get("default_top_k", 5)),
                    ),
                    default=5,
                ),
                max_context_chars=_as_int(
                    os.getenv(
                        "RFP_RAG_MAX_CONTEXT_CHARS",
                        env_values.get("RFP_RAG_MAX_CONTEXT_CHARS", retrieval_config.get("max_context_chars", 12000)),
                    ),
                    default=12000,
                ),
                keyword_weight=float(
                    os.getenv(
                        "RFP_RAG_KEYWORD_WEIGHT",
                        env_values.get("RFP_RAG_KEYWORD_WEIGHT", retrieval_config.get("keyword_weight", 0.35)),
                    )
                ),
                semantic_weight=float(
                    os.getenv(
                        "RFP_RAG_SEMANTIC_WEIGHT",
                        env_values.get("RFP_RAG_SEMANTIC_WEIGHT", retrieval_config.get("semantic_weight", 0.65)),
                    )
                ),
                require_approved_answers=_as_bool(
                    os.getenv(
                        "RFP_RAG_REQUIRE_APPROVED_ANSWERS",
                        env_values.get(
                            "RFP_RAG_REQUIRE_APPROVED_ANSWERS",
                            retrieval_config.get("require_approved_answers", False),
                        ),
                    ),
                    default=False,
                ),
            ),
            ingestion=IngestionSettings(
                word_chunk_max_chars=_as_int(
                    os.getenv(
                        "RFP_RAG_WORD_CHUNK_MAX_CHARS",
                        env_values.get(
                            "RFP_RAG_WORD_CHUNK_MAX_CHARS",
                            ingestion_config.get("word_chunk_max_chars", 4000),
                        ),
                    ),
                    default=4000,
                ),
                excel_row_group_size=_as_int(
                    os.getenv(
                        "RFP_RAG_EXCEL_ROW_GROUP_SIZE",
                        env_values.get(
                            "RFP_RAG_EXCEL_ROW_GROUP_SIZE",
                            ingestion_config.get("excel_row_group_size", 1),
                        ),
                    ),
                    default=1,
                ),
                preserve_tables=_as_bool(
                    os.getenv(
                        "RFP_RAG_PRESERVE_TABLES",
                        env_values.get("RFP_RAG_PRESERVE_TABLES", ingestion_config.get("preserve_tables", True)),
                    ),
                    default=True,
                ),
                detect_question_answer_blocks=_as_bool(
                    os.getenv(
                        "RFP_RAG_DETECT_QA_BLOCKS",
                        env_values.get(
                            "RFP_RAG_DETECT_QA_BLOCKS",
                            ingestion_config.get("detect_question_answer_blocks", True),
                        ),
                    ),
                    default=True,
                ),
            ),
        )
