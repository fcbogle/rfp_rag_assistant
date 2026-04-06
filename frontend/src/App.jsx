import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const TERMINAL_JOB_STATUSES = new Set(["completed", "completed_with_errors", "failed"]);

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
  const [activeView, setActiveView] = useState("documents");
  const [scopeState, setScopeState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [selectedScope, setSelectedScope] = useState({
    rfp_id: "",
    submission_id: "",
  });
  const [health, setHealth] = useState(null);
  const [corpusInfoState, setCorpusInfoState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [documentsState, setDocumentsState] = useState({
    loading: true,
    error: "",
    data: null,
  });
  const [sourceStatusState, setSourceStatusState] = useState({
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
    combined_qa: false,
    response_supporting_material: false,
    background_requirements: false,
    tender_details: false,
    external_reference: false,
    "reference-combined_qa": false,
    "reference-response_supporting_material": false,
    "reference-background_requirements": false,
    "reference-tender_details": false,
    "reference-external_reference": false,
    "ingest-combined_qa": false,
    "ingest-response_supporting_material": false,
    "ingest-background_requirements": false,
    "ingest-tender_details": false,
    "ingest-external_reference": false,
    "classification-combined_qa": false,
    "classification-response_supporting_material": false,
    "classification-background_requirements": false,
    "classification-tender_details": false,
    "classification-external_reference": false,
  });

  useEffect(() => {
    void loadHealth();
    void loadScopes();
  }, []);

  useEffect(() => {
    if (!selectedScope.rfp_id && !selectedScope.submission_id) {
      return;
    }
    setIngestionState({ loading: false, error: "", data: null });
    void loadCorpusInfo(selectedScope);
    void loadDocuments(selectedScope);
    void loadSourceStatus(selectedScope);
    void loadReferenceUrls(selectedScope);
  }, [selectedScope.rfp_id, selectedScope.submission_id]);

  useEffect(() => {
    const activeJob = ingestionState.data ?? sourceStatusState.data?.active_job;
    if (!activeJob?.job_id || TERMINAL_JOB_STATUSES.has(activeJob.status)) {
      return undefined;
    }

    const handle = window.setInterval(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/ingestion/jobs/${activeJob.job_id}`);
        if (!response.ok) {
          throw new Error(`Job polling failed with status ${response.status}`);
        }
        const payload = await response.json();
        setIngestionState((current) => ({ ...current, loading: false, data: payload.job }));
        await loadSourceStatus(selectedScope);
        await loadDocuments(selectedScope);
      } catch (error) {
        setIngestionState((current) => ({ ...current, loading: false, error: error.message }));
      }
    }, 1500);

    return () => window.clearInterval(handle);
  }, [
    ingestionState.data?.job_id,
    ingestionState.data?.status,
    sourceStatusState.data?.active_job?.job_id,
    sourceStatusState.data?.active_job?.status,
    selectedScope.rfp_id,
    selectedScope.submission_id,
  ]);

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

  async function loadScopes() {
    setScopeState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/rfp-scopes`);
      if (!response.ok) {
        throw new Error(`Scope listing failed with status ${response.status}`);
      }
      const data = await response.json();
      setScopeState({ loading: false, error: "", data });
      if (data.scopes?.length) {
        const first = data.scopes[0];
        setSelectedScope({
          rfp_id: first.rfp_id,
          submission_id: first.submission_id,
        });
      }
    } catch (error) {
      setScopeState({ loading: false, error: error.message, data: null });
    }
  }

  function buildScopeQuery(scope) {
    const params = new URLSearchParams();
    if (scope?.rfp_id) {
      params.set("rfp_id", scope.rfp_id);
    }
    if (scope?.submission_id) {
      params.set("submission_id", scope.submission_id);
    }
    const query = params.toString();
    return query ? `?${query}` : "";
  }

  async function loadDocuments(scope = selectedScope) {
    setDocumentsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/documents${buildScopeQuery(scope)}`);
      if (!response.ok) {
        throw new Error(`Document listing failed with status ${response.status}`);
      }
      const data = await response.json();
      setDocumentsState({ loading: false, error: "", data });
    } catch (error) {
      setDocumentsState({ loading: false, error: error.message, data: null });
    }
  }

  async function loadSourceStatus(scope = selectedScope) {
    setSourceStatusState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/ingestion/source-status${buildScopeQuery(scope)}`);
      if (!response.ok) {
        throw new Error(`Source status request failed with status ${response.status}`);
      }
      const data = await response.json();
      setSourceStatusState({ loading: false, error: "", data });
      if (!ingestionState.data && data.active_job) {
        setIngestionState((current) => ({ ...current, data: data.active_job }));
      }
    } catch (error) {
      setSourceStatusState({ loading: false, error: error.message, data: null });
    }
  }

  async function loadCorpusInfo(scope = selectedScope) {
    setCorpusInfoState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/corpus-info${buildScopeQuery(scope)}`);
      if (!response.ok) {
        throw new Error(`Corpus information request failed with status ${response.status}`);
      }
      const data = await response.json();
      setCorpusInfoState({ loading: false, error: "", data });
    } catch (error) {
      setCorpusInfoState({ loading: false, error: error.message, data: null });
    }
  }

  async function loadReferenceUrls(scope = selectedScope) {
    setReferenceUrlsState((current) => ({ ...current, loading: true, error: "" }));
    try {
      const response = await fetch(`${API_BASE_URL}/reference-urls${buildScopeQuery(scope)}`);
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

  const groupedSourceStatus = sourceStatusState.data
    ? Object.keys(sourceStatusState.data.counts_by_document_type)
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
          items: sourceStatusState.data.items.filter((item) => item.document_type === documentType),
        }))
        .filter((group) => group.items.length > 0)
    : [];

  const activeIngestionJob =
    sourceStatusState.data?.active_job && !TERMINAL_JOB_STATUSES.has(sourceStatusState.data.active_job.status)
      ? sourceStatusState.data.active_job
      : ingestionState.data ?? sourceStatusState.data?.active_job ?? null;
  const activeJobIsRunning =
    activeIngestionJob && !TERMINAL_JOB_STATUSES.has(activeIngestionJob.status);

  async function startIngestionJob({ documentTypes = null, sourceFiles = null } = {}) {
    setIngestionState({ loading: true, error: "", data: null });

    try {
      const payload = {
        ...form,
        submission_id: selectedScope.submission_id || null,
        document_types:
          documentTypes ?? (selectedDocumentTypes.length > 0 ? selectedDocumentTypes : null),
        source_files: sourceFiles,
        limit: Number(form.limit) || null,
      };

      const response = await fetch(`${API_BASE_URL}/ingestion/jobs`, {
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
      setIngestionState({ loading: false, error: "", data: data.job });
      void loadSourceStatus();
      void loadDocuments();
    } catch (error) {
      setIngestionState({ loading: false, error: error.message, data: null });
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await startIngestionJob();
  }

  function renderSourceInventory() {
    return (
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
    );
  }

  const availableScopes = scopeState.data?.scopes ?? [];
  const selectedScopeRecord = availableScopes.find(
    (scope) => scope.rfp_id === selectedScope.rfp_id && scope.submission_id === selectedScope.submission_id,
  );
  const selectedTargetCollections = corpusInfoState.data
    ? corpusInfoState.data.chroma.target_collections.filter((item) =>
        selectedDocumentTypes.includes(item.document_type),
      )
    : [];

  function renderIngestionSourceStatus() {
    return (
      <section className="panel panel-side-summary panel-span">
        <div className="panel-header">
          <h2>Source ingestion status</h2>
          <p>
            This is the operational control surface for ingestion jobs. Start classification or
            file-level runs here and monitor progress against each source item.
          </p>
        </div>
        <div className="ingestion-actions">
          <button
            className="primary-button"
            type="button"
            disabled={ingestionState.loading || activeJobIsRunning}
            onClick={() => void startIngestionJob()}
          >
            {activeJobIsRunning ? "Job running..." : "Run selected classifications"}
          </button>
          <button
            className="ghost-button"
            type="button"
            onClick={() => void loadSourceStatus()}
          >
            Refresh source status
          </button>
        </div>

        {ingestionState.error ? <p className="error-text">{ingestionState.error}</p> : null}
        {sourceStatusState.error ? <p className="error-text">{sourceStatusState.error}</p> : null}

        {activeIngestionJob ? (
          <div className="progress-block">
            <div className="progress-header">
              <strong>
                {activeIngestionJob.status === "queued"
                  ? "Queued"
                  : activeIngestionJob.status === "running"
                    ? "In progress"
                    : "Last job"}
              </strong>
              <span>
                {activeIngestionJob.processed_documents}/{activeIngestionJob.total_documents} documents
              </span>
            </div>
            <div className="progress-track">
              <div
                className={`progress-bar ${activeJobIsRunning ? "indeterminate" : ""}`}
                style={
                  activeJobIsRunning
                    ? undefined
                    : { width: `${activeIngestionJob.progress_percent || 0}%` }
                }
              />
            </div>
            <p className="muted-text">
              {activeIngestionJob.current_phase} · {activeIngestionJob.total_chunks} chunks
            </p>
            {activeIngestionJob.errors?.length ? (
              <div className="job-error-list">
                {activeIngestionJob.errors.map((error) => (
                  <p className="error-text compact-error" key={error}>
                    {error}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {sourceStatusState.data ? (
          <div className="accordion-list">
            {groupedSourceStatus.map((group) => (
              <section className="accordion-section" key={`ingest-${group.documentType}`}>
                <div className="accordion-row">
                  <button
                    className="accordion-trigger"
                    type="button"
                    onClick={() => toggleOpenSection(`ingest-${group.documentType}`)}
                  >
                    <span>
                      <strong>{group.documentType}</strong>
                      <small>{group.items.length} files</small>
                    </span>
                    <span className={`accordion-chevron ${openSections[`ingest-${group.documentType}`] ? "open" : ""}`}>
                      ▾
                    </span>
                  </button>
                  <button
                    className="ghost-button classification-action"
                    type="button"
                    disabled={ingestionState.loading || activeJobIsRunning}
                    onClick={() => void startIngestionJob({ documentTypes: [group.documentType] })}
                  >
                    Ingest classification
                  </button>
                </div>
                {openSections[`ingest-${group.documentType}`] ? (
                  <div className="status-list">
                    {group.items.map((document) => (
                      <article className="status-item status-item-grid" key={`ingest-${document.source_file}`}>
                        <div className="status-item-main">
                          <strong>{document.source_file}</strong>
                          <small>
                            {document.file_type}
                            {document.chunk_count ? ` · ${document.chunk_count} chunks` : ""}
                          </small>
                          {document.last_error ? (
                            <small className="status-error-text">{document.last_error}</small>
                          ) : null}
                        </div>
                        <div className="status-item-tags">
                          <span className={`reference-status status-${document.support_status}`}>
                            {document.support_status}
                          </span>
                          <span className={`reference-status status-${document.ingestion_status}`}>
                            {document.ingestion_status}
                          </span>
                        </div>
                        <div className="status-item-actions">
                          <button
                            className="ghost-button row-action-button"
                            type="button"
                            disabled={ingestionState.loading || activeJobIsRunning}
                            onClick={() => void startIngestionJob({ sourceFiles: [document.source_file] })}
                          >
                            {document.ingestion_status === "failed" ? "Retry file" : "Ingest file"}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                ) : null}
              </section>
            ))}
          </div>
        ) : (
          <p className="muted-text">Loading ingestion source status...</p>
        )}
      </section>
    );
  }

  return (
    <div className="app-shell">
      <nav className="top-nav">
        <div className="brand-block">
          <div className="nav-brand-row">
            <img className="nav-logo" src="/blatchford-mark.jpeg" alt="Blatchford mark" />
            <div className="nav-title-block">
              <strong>RFP RAG Assistant</strong>
              <span className="nav-subtitle">Internal response intelligence workspace</span>
            </div>
          </div>
          <span className="brand-kicker">Blatchford RFP Workspace</span>
        </div>
        <div className="nav-links">
          <button
            className={`nav-link ${activeView === "documents" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveView("documents")}
          >
            Documents
          </button>
          <button
            className={`nav-link ${activeView === "ingestion" ? "active" : ""}`}
            type="button"
            onClick={() => setActiveView("ingestion")}
          >
            Ingestion
          </button>
          <span className="nav-link nav-link-disabled">Query</span>
        </div>
      </nav>

      <header className="hero">
        <div className="hero-copy-block">
          {activeView === "documents" ? (
            <>
              <p className="eyebrow">Source Inventory</p>
              <h1>Understand the RFP corpus before ingestion</h1>
              <p className="hero-copy">
                Review corpus rationale, storage locations, classifications, uploaded files, and
                reviewed URLs so the source model is clear before any indexing run is triggered.
              </p>
            </>
          ) : (
            <>
              <p className="eyebrow">Ingestion Control</p>
              <h1>Run controlled indexing into the right collections</h1>
              <p className="hero-copy">
                Set run-level RFP metadata, choose classifications, and execute synchronous
                ingestion into Chroma with a clear summary of what changed.
              </p>
            </>
          )}
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

      <section className="scope-bar">
        <div className="scope-bar-copy">
          <strong>Active RFP scope</strong>
          <p>Use these selectors to view the corpus and source inventory for a specific RFP and submission set.</p>
        </div>
        <div className="scope-selectors">
          <label>
            <span>RFP</span>
            <select
              value={selectedScope.rfp_id}
              onChange={(event) => {
                const next = availableScopes.find((scope) => scope.rfp_id === event.target.value);
                setSelectedScope({
                  rfp_id: event.target.value,
                  submission_id: next?.submission_id ?? "",
                });
              }}
            >
              {availableScopes.map((scope) => (
                <option key={`${scope.rfp_id}-${scope.submission_id}`} value={scope.rfp_id}>
                  {scope.rfp_title}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Submission</span>
            <select
              value={selectedScope.submission_id}
              onChange={(event) =>
                setSelectedScope((current) => ({
                  ...current,
                  submission_id: event.target.value,
                }))
              }
            >
              {availableScopes
                .filter((scope) => scope.rfp_id === selectedScope.rfp_id)
                .map((scope) => (
                  <option key={scope.submission_id} value={scope.submission_id}>
                    {scope.submission_title}
                  </option>
                ))}
            </select>
          </label>
        </div>
        <div className="scope-summary">
          <span>{selectedScopeRecord?.issuing_authority ?? "No scope selected"}</span>
        </div>
      </section>

      {activeView === "documents" ? (
        <main className="documents-layout">
          <div className="documents-overview-grid">
            <section className="panel panel-intro">
              <div className="panel-header">
                <h2>Blob source corpus</h2>
                <p>
                  This section describes the primary file-source corpus before ingestion into
                  Chroma.
                </p>
              </div>
              {corpusInfoState.data ? (
                <div className="info-list">
                  <div><span>Account</span><strong>{corpusInfoState.data.blob.account ?? "Not configured"}</strong></div>
                  <div><span>Container</span><strong>{corpusInfoState.data.blob.container}</strong></div>
                  <div><span>Prefix</span><strong>{corpusInfoState.data.blob.prefix || "/"}</strong></div>
                  <div><span>Region</span><strong>{corpusInfoState.data.blob.region ?? "Not surfaced"}</strong></div>
                  <div><span>File types</span><strong>{corpusInfoState.data.blob.supported_extensions.join(", ")}</strong></div>
                </div>
              ) : (
                <p className="muted-text">{corpusInfoState.loading ? "Loading corpus information..." : corpusInfoState.error}</p>
              )}
            </section>

            <section className="panel panel-intro">
              <div className="panel-header">
                <h2>Chroma corpus</h2>
                <p>Target collection design for indexed content and retrieval.</p>
              </div>
              {corpusInfoState.data ? (
                <div className="info-list">
                  <div><span>Endpoint</span><strong>{corpusInfoState.data.chroma.endpoint ?? "Not configured"}</strong></div>
                  <div><span>Database</span><strong>{corpusInfoState.data.chroma.database ?? "Not configured"}</strong></div>
                  <div><span>Region</span><strong>{corpusInfoState.data.chroma.region ?? "Not surfaced"}</strong></div>
                  <div><span>Namespace</span><strong>{corpusInfoState.data.chroma.namespace}</strong></div>
                  <div><span>Collection base</span><strong>{corpusInfoState.data.chroma.collection_base}</strong></div>
                </div>
              ) : (
                <p className="muted-text">{corpusInfoState.loading ? "Loading Chroma information..." : corpusInfoState.error}</p>
              )}
            </section>
          </div>

          <section className="panel">
            <div className="panel-header">
              <h2>Corpus classifications</h2>
              <p>
                These categories describe the planned RFP corpus structure and why each classification
                exists.
              </p>
            </div>
            {corpusInfoState.data ? (
              <div className="accordion-list">
                {corpusInfoState.data.classifications.map((item) => (
                  <section className="accordion-section" key={item.document_type}>
                    <button
                      className="accordion-trigger"
                      type="button"
                      onClick={() => toggleOpenSection(`classification-${item.document_type}`)}
                    >
                      <span>
                        <strong>{item.document_type}</strong>
                        <small>{item.title}</small>
                      </span>
                      <span
                        className={`accordion-chevron ${
                          openSections[`classification-${item.document_type}`] ? "open" : ""
                        }`}
                      >
                        ▾
                      </span>
                    </button>
                    {openSections[`classification-${item.document_type}`] ? (
                      <article className="classification-card">
                        <span className="classification-kicker">{item.document_type}</span>
                        <h3>{item.title}</h3>
                        <p>{item.purpose}</p>
                        <p><strong>Why it exists:</strong> {item.rationale}</p>
                        <p><strong>Primary value:</strong> {item.primary_value}</p>
                      </article>
                    ) : null}
                  </section>
                ))}
              </div>
            ) : (
              <p className="muted-text">{corpusInfoState.loading ? "Loading classification rationale..." : corpusInfoState.error}</p>
            )}
          </section>
          {renderSourceInventory()}
        </main>
      ) : (
        <main className="layout-grid">
          <section className="panel panel-form">
            <div className="panel-header">
              <h2>Ingestion Run</h2>
              <p>Set run-level metadata once. Use the source status card to trigger and monitor jobs.</p>
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
            </form>
            <p className="muted-text">
              The selected classifications and file-level actions in Source ingestion status will
              use this metadata for each ingestion job.
            </p>
          </section>
          <section className="panel panel-side-summary">
            <div className="panel-header">
              <h2>Run metadata and corpus scope</h2>
              <p>
                Choose which classifications to process, then run indexing against the target Chroma collections.
              </p>
            </div>
            <div className="context-sections">
              <div className="context-block">
                <span className="context-heading">Active scope</span>
                <div className="info-list compact-info-list">
                  <div><span>RFP title</span><strong>{selectedScopeRecord?.rfp_title ?? form.rfp_title}</strong></div>
                  <div><span>Submission</span><strong>{selectedScopeRecord?.submission_title ?? "Current selection"}</strong></div>
                  <div><span>Authority</span><strong>{selectedScopeRecord?.issuing_authority ?? form.issuing_authority}</strong></div>
                  <div><span>Response owner</span><strong>{selectedScopeRecord?.response_owner ?? form.customer}</strong></div>
                </div>
              </div>

              <div className="context-block">
                <span className="context-heading">Selected classifications</span>
                <div className="chip-grid chip-grid-readonly">
                  {selectedDocumentTypes.map((documentType) => (
                    <span className="chip-option chip-option-static" key={documentType}>
                      <span>{documentType}</span>
                    </span>
                  ))}
                </div>
              </div>

              <div className="context-block">
                <span className="context-heading">Source and target stores</span>
                <div className="info-list compact-info-list">
                  <div><span>Blob container</span><strong>{corpusInfoState.data?.blob.container ?? "..."}</strong></div>
                  <div><span>Blob prefix</span><strong>{corpusInfoState.data?.blob.prefix || "/"}</strong></div>
                  <div><span>Blob region</span><strong>{corpusInfoState.data?.blob.region ?? "Not surfaced"}</strong></div>
                  <div><span>Chroma region</span><strong>{corpusInfoState.data?.chroma.region ?? "Not surfaced"}</strong></div>
                  <div><span>Chroma namespace</span><strong>{corpusInfoState.data?.chroma.namespace ?? "..."}</strong></div>
                  <div><span>Collection base</span><strong>{corpusInfoState.data?.chroma.collection_base ?? "..."}</strong></div>
                </div>
              </div>

              <div className="context-block">
                <span className="context-heading">Target collections</span>
                <div className="collection-list">
                  {selectedTargetCollections.length ? (
                    selectedTargetCollections.map((item) => (
                      <div className="collection-item" key={item.collection_name}>
                        <span>{item.document_type}</span>
                        <strong>{item.collection_name}</strong>
                      </div>
                    ))
                  ) : (
                    <p className="muted-text">No target collections resolved yet.</p>
                  )}
                </div>
              </div>

              <div className="summary-grid compact-summary-grid">
                <article className="summary-card">
                  <span>Available files</span>
                  <strong>{documentsState.data?.document_count ?? "..."}</strong>
                </article>
                <article className="summary-card">
                  <span>Reviewed URLs</span>
                  <strong>{referenceUrlsState.data?.reference_url_count ?? "..."}</strong>
                </article>
                <article className="summary-card">
                  <span>Limit</span>
                  <strong>{form.limit || "All"}</strong>
                </article>
                <article className="summary-card">
                  <span>Mode</span>
                  <strong>Tracked job</strong>
                </article>
              </div>
            </div>
          </section>
          {renderIngestionSourceStatus()}
        </main>
      )}
    </div>
  );
}

export default App;
