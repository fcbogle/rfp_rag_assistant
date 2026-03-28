# rfp_rag_assistant

RFP knowledge reuse and grounded response generation assistant.

## Scope

This project is structured for:

- Word and Excel ingestion
- structure-aware chunking
- metadata-rich retrieval
- grounded answer generation
- source traceability

## Layout

The codebase uses a `src/` layout with the package at `src/rfp_rag_assistant/`.

## Quick Start

Create an environment and install in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

Run the CLI:

```bash
PYTHONPATH=src python -m rfp_rag_assistant.app.cli
```

Run tests:

```bash
python -m pytest -q
```

## Configuration

Runtime settings are loaded in this order:

1. defaults in code
2. `config/app.toml`
3. `.env`
4. exported shell environment variables

Start from `.env.example` and adjust local values in `.env`.

The config shape is organised around:

- OpenAI chat settings
- Azure OpenAI deployment settings
- Chroma vector store settings
- retrieval defaults
- ingestion defaults

For token sizing, prefer the RFP-native env vars:

- `RFP_RAG_CHUNK_SIZE_TOKENS`
- `RFP_RAG_OVERLAP_TOKENS`
