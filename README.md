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
python -m rfp_rag_assistant.app.cli
```

Run tests:

```bash
python -m pytest -q
```
