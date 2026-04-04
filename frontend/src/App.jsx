import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const DOCUMENT_TYPES = [
  "combined_qa",
  "response_supporting_material",
  "background_requirements",
  "tender_details",
  "external_reference",
];

const INITIAL_FORM = {
  issuing_authority: "Sussex Community NHS Foundation Trust",
  customer: "Sussex Community NHS Foundation Trust",
  rfp_id: "scft-wheelchair-2026",
  rfp_title: "Wheelchair and Specialist Seating Service",
  limit: 5,
};

function App() {
  const [health, setHealth] = useState(null);
  const [documentsState, setDocumentsState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [ingestionState, setIngestionState] = useState({
    loading: false,
    error: "",
    data: null,
  });
  const [referenceUrlsState, setReferenceUrlsState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [form, setForm] = useState(INITIAL_FORM);
  const [selectedDocumentTypes, setSelectedDocumentTypes] = useState(["combined_qa"]);
  const [openSections, setOpenSections] = useState({
    combined_qa: true,
    response_supporting_material: false,
    background_requirements: false,
    tender_details: false,
    external_reference: false,
  });

  useEffect(() => {
    void loadHealth();
    void loadDocuments();
    void loadReferenceUrls();
  }, []);

  async function loadHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (!response.ok) {
        throw new Error(`Health check failed with status ${response.status}`);
      }
      const data = await response.json();
      setHealth({ ...data, ok: true });
    } catch (error) {
      setHealth({ ok: false, detail: error.message });
    }
  }

  async function loadDocuments() {
    setDocumentsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/documents`);
      if (!response.ok) {
        throw new Error(`Document listing failed with status ${response.status}`);
      }
      const data = await response.json();
      setDocumentsState({ loading: false, error: "", data });
    } catch (error) {
      setDocumentsState({ loading: false, error: error.message, data: null });
    }
  }

  async function loadReferenceUrls() {
    setReferenceUrlsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/reference-urls`);
      if (!response.ok) {
        throw new Error(`Reference URL listing failed with status ${response.status}`);
      }
      const data = await response.json();
      setReferenceUrlsState({ loading: false, error: "", data });
    } catch (error) {
      setReferenceUrlsState({ loading: false, error: error.message, data: null });
    }
  }

  function toggleDocumentType(documentType) {
    setSelectedDocumentTypes((current) => {
      if (current.includes(documentType)) {
        return current.filter((value) => value !== documentType);
      }
      return [...current, documentType];
    });
  }

  function toggleOpenSection(documentType) {
    setOpenSections((current) => ({
      ...current,
      [documentType]: !current[documentType],
    }));
  }

  const groupedDocuments = documentsState.data
    ? Object.keys(documentsState.data.counts_by_document_type)
        .sort((left, right) => {
          const leftIndex = DOCUMENT_TYPES.indexOf(left);
          const rightIndex = DOCUMENT_TYPES.indexOf(right);
          if (leftIndex === -1 && rightIndex === -1) {
            return left.localeCompare(right);
          }
          if (leftIndex === -1) {
            return 1;
          }
          if (rightIndex === -1) {
            return -1;
          }
          return leftIndex - rightIndex;
        })
        .map((documentType) => ({
          documentType,
          documents: documentsState.data.documents.filter(
            (document) => document.document_type === documentType,
          ),
        }))
        .filter((group) => group.documents.length > 0)
    : [];

  const groupedReferenceUrls = referenceUrlsState.data
    ? Object.keys(referenceUrlsState.data.counts_by_document_type)
        .sort((left, right) => {
          const leftIndex = DOCUMENT_TYPES.indexOf(left);
          const rightIndex = DOCUMENT_TYPES.indexOf(right);
          if (leftIndex === -1 && rightIndex === -1) {
            return left.localeCompare(right);
          }
          if (leftIndex === -1) {
            return 1;
          }
          if (rightIndex === -1) {
            return -1;
          }
          return leftIndex - rightIndex;
        })
        .map((documentType) => ({
          documentType,
          items: referenceUrlsState.data.items.filter((item) => item.document_type === documentType),
        }))
        .filter((group) => group.items.length > 0)
    : [];

  async function handleSubmit(event) {
    event.preventDefault();
    setIngestionState({ loading: true, error: "", data: null });

    try {
      const payload = {
        ...form,
        document_types: selectedDocumentTypes.length > 0 ? selectedDocumentTypes : null,
        limit: Number(form.limit) || null,
      };

      const response = await fetch(`${API_BASE_URL}/ingestion`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const text = await response.text();
        throw new Error(text || `Ingestion failed with status ${response.status}`);
      }

      const data = await response.json();
      setIngestionState({ loading: false, error: "", data });
      void loadDocuments();
    } catch (error) {
      setIngestionState({ loading: false, error: error.message, data: null });
    }
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <div className="brand-block">
          <div className="nav-brand-row">
            <img className="nav-logo" src="/blatchford-logo.png" alt="Blatchford logo" />
            <div className="nav-title-block">
              <strong>RFP RAG Assistant</strong>
              <span className="nav-subtitle">Internal response intelligence workspace</span>
            </div>
          </div>
          <span className="brand-kicker">Blatchford RFP Workspace</span>
        </div>
        <div className="nav-links">
          <span className="nav-link active">Ingestion</span>
          <span className="nav-link">Documents</span>
          <span className="nav-link">Query</span>
        </div>
      </nav>

      <header className="hero">
        <div className="hero-copy-block">
          <p className="eyebrow">RFP RAG Assistant</p>
          <h1>Document organisation and ingestion</h1>
          <p className="hero-copy">
            Organise premium RFP source material, validate corpus coverage, and run controlled
            ingestion into Chroma before moving to retrieval and draft support.
          </p>
        </div>
        <div className="status-card">
          <span className="status-label">Backend status</span>
          <span className={`status-pill ${health?.ok ? "ok" : "warn"}`}>
            {health?.ok ? "API Ready" : "API Check Pending"}
          </span>
          <p className="status-detail">
            {health?.ok ? "FastAPI runtime is reachable." : health?.detail ?? "Waiting for health response."}
          </p>
        </div>
      </header>

      <main className="layout-grid">
        <section className="panel panel-form">
          <div className="panel-header">
            <h2>Ingestion Run</h2>
            <p>Set run-level metadata once, then trigger a synchronous ingestion batch.</p>
          </div>

          <form className="ingestion-form" onSubmit={handleSubmit}>
            <label>
              <span>Issuing authority</span>
              <input
                value={form.issuing_authority}
                onChange={(event) => setForm({ ...form, issuing_authority: event.target.value })}
              />
            </label>

            <label>
              <span>Customer</span>
              <input
                value={form.customer}
                onChange={(event) => setForm({ ...form, customer: event.target.value })}
              />
            </label>

            <div className="field-row">
              <label>
                <span>RFP ID</span>
                <input
                  value={form.rfp_id}
                  onChange={(event) => setForm({ ...form, rfp_id: event.target.value })}
                />
              </label>
              <label>
                <span>Limit</span>
                <input
                  type="number"
                  min="1"
                  value={form.limit}
                  onChange={(event) => setForm({ ...form, limit: event.target.value })}
                />
              </label>
            </div>

            <label>
              <span>RFP title</span>
              <input
                value={form.rfp_title}
                onChange={(event) => setForm({ ...form, rfp_title: event.target.value })}
              />
            </label>

            <fieldset className="document-types">
              <legend>Document classifications</legend>
              <div className="chip-grid">
                {DOCUMENT_TYPES.map((documentType) => (
                  <label className="chip-option" key={documentType}>
                    <input
                      type="checkbox"
                      checked={selectedDocumentTypes.includes(documentType)}
                      onChange={() => toggleDocumentType(documentType)}
                    />
                    <span>{documentType}</span>
                  </label>
                ))}
              </div>
            </fieldset>

            <button className="primary-button" type="submit" disabled={ingestionState.loading}>
              {ingestionState.loading ? "Running ingestion..." : "Run ingestion"}
            </button>
          </form>

          {ingestionState.error ? <p className="error-text">{ingestionState.error}</p> : null}

          {ingestionState.loading ? (
            <div className="progress-block">
              <div className="progress-track">
                <div className="progress-bar" />
              </div>
              <p>Ingestion is running synchronously. Results will appear below when complete.</p>
            </div>
          ) : null}

          {ingestionState.data ? (
            <div className="result-card">
              <div className="result-metrics">
                <div>
                  <strong>{ingestionState.data.document_count}</strong>
                  <span>documents</span>
                </div>
                <div>
                  <strong>{ingestionState.data.chunk_count}</strong>
                  <span>chunks</span>
                </div>
                <div>
                  <strong>{ingestionState.data.indexing.total_chunks}</strong>
                  <span>indexed</span>
                </div>
              </div>
              <pre>{JSON.stringify(ingestionState.data, null, 2)}</pre>
            </div>
          ) : null}
        </section>

        <div className="panel-stack">
          <section className="panel">
            <div className="panel-header">
              <h2>Blob Documents</h2>
              <p>Live view of the source files currently available to the ingestion service.</p>
            </div>

            <div className="toolbar">
              <button className="ghost-button" type="button" onClick={() => void loadDocuments()}>
                Refresh
              </button>
            </div>

            {documentsState.error ? <p className="error-text">{documentsState.error}</p> : null}

            {documentsState.loading ? (
              <p className="muted-text">Loading Blob document inventory...</p>
            ) : null}

            {documentsState.data ? (
              <>
                <div className="summary-grid">
                  <article className="summary-card">
                    <span>Total documents</span>
                    <strong>{documentsState.data.document_count}</strong>
                  </article>
                  {Object.entries(documentsState.data.counts_by_document_type).map(([key, value]) => (
                    <article className="summary-card" key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </article>
                  ))}
                </div>

                <div className="accordion-list">
                  {groupedDocuments.map((group) => (
                    <section className="accordion-section" key={group.documentType}>
                      <button
                        className="accordion-trigger"
                        type="button"
                        onClick={() => toggleOpenSection(group.documentType)}
                      >
                        <span>
                          <strong>{group.documentType}</strong>
                          <small>{group.documents.length} files</small>
                        </span>
                        <span className={`accordion-chevron ${openSections[group.documentType] ? "open" : ""}`}>
                          ▾
                        </span>
                      </button>

                      {openSections[group.documentType] ? (
                        <div className="table-shell">
                          <table>
                            <thead>
                              <tr>
                                <th>Source file</th>
                                <th>Type</th>
                              </tr>
                            </thead>
                            <tbody>
                              {group.documents.map((document) => (
                                <tr key={document.source_file}>
                                  <td>{document.source_file}</td>
                                  <td>{document.file_type}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : null}
                    </section>
                  ))}
                </div>
              </>
            ) : null}
          </section>

          <section className="panel">
            <div className="panel-header">
              <h2>Reference URLs</h2>
              <p>
                Reviewed external references found in the RFP material. This card helps users see
                the broader source context before ingestion decisions are made.
              </p>
            </div>

            {referenceUrlsState.error ? <p className="error-text">{referenceUrlsState.error}</p> : null}

            {referenceUrlsState.loading ? (
              <p className="muted-text">Loading reviewed reference URL inventory...</p>
            ) : null}

            {referenceUrlsState.data ? (
              <>
                <div className="summary-grid">
                  <article className="summary-card">
                    <span>Total URLs</span>
                    <strong>{referenceUrlsState.data.reference_url_count}</strong>
                  </article>
                  {Object.entries(referenceUrlsState.data.counts_by_status).map(([key, value]) => (
                    <article className="summary-card" key={key}>
                      <span>{key}</span>
                      <strong>{value}</strong>
                    </article>
                  ))}
                </div>

                <div className="accordion-list">
                  {groupedReferenceUrls.map((group) => (
                    <section className="accordion-section" key={`reference-${group.documentType}`}>
                      <button
                        className="accordion-trigger"
                        type="button"
                        onClick={() => toggleOpenSection(`reference-${group.documentType}`)}
                      >
                        <span>
                          <strong>{group.documentType}</strong>
                          <small>{group.items.length} URLs</small>
                        </span>
                        <span className={`accordion-chevron ${openSections[`reference-${group.documentType}`] ? "open" : ""}`}>
                          ▾
                        </span>
                      </button>

                      {openSections[`reference-${group.documentType}`] ? (
                        <div className="reference-list">
                          {group.items.map((item) => (
                            <article className="reference-item" key={item.url}>
                              <div className="reference-meta">
                                <span className={`reference-status status-${item.status}`}>{item.status}</span>
                                <span className="reference-origin">{item.reference_origin}</span>
                                <span className="reference-format">{item.source_format}</span>
                              </div>
                              <a className="reference-link" href={item.url} target="_blank" rel="noreferrer">
                                {item.url}
                              </a>
                            </article>
                          ))}
                        </div>
                      ) : null}
                    </section>
                  ))}
                </div>
              </>
            ) : null}
          </section>
        </div>
      </main>
    </div>
  );
}

export default App;
