# Frontend

Minimal React UI for:

- listing Blob-backed source documents
- triggering synchronous ingestion runs
- inspecting ingestion summaries

## Run

From the `frontend` directory:

```bash
npm install
npm run dev
```

The app expects the FastAPI backend at:

```text
http://localhost:8000
```

Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Backend

Start the API from the repo root:

```bash
.venv/bin/python -m uvicorn rfp_rag_assistant.api:create_api_app --factory --reload
```
