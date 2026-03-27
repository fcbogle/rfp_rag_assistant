# AGENTS.md

## Purpose

This repository implements an LLM RAG-based assistant to support responses to RFPs (Requests for Proposal).

The system will:
- ingest historical RFPs and responses from Word and Excel
- extract and structure question/answer pairs
- retrieve relevant prior answers
- generate grounded draft responses
- provide traceability to source content

This is a knowledge-assistant and response-generation system, not a regulatory analysis system.

---

## Reference Project: IFULLMDEV

A separate project, IFULLMDEV, is available as a reference implementation.

Use IFULLMDEV for:
- ingestion pipeline structure
- metadata handling concepts
- chunking framework concepts
- embedding/indexing patterns
- retrieval orchestration ideas
- logging and traceability patterns

IMPORTANT:
- IFULLMDEV is READ-ONLY
- DO NOT modify or refactor IFULLMDEV
- DO NOT copy PDF-specific parsing logic into this repository unless explicitly instructed
- Reimplement useful patterns in this repository, adapted for RFP use cases

---

## Important Difference from IFULLMDEV

IFULLMDEV primarily ingests PDF documents and relies on PDF text extraction and section parsing.

This project ingests:
- Word documents (.docx)
- Excel spreadsheets (.xlsx)

Therefore:

- DO NOT reuse PDF parsing logic from IFULLMDEV
- DO reuse high-level patterns such as:
  - ingestion pipeline design
  - metadata enrichment
  - chunk lifecycle and preparation
  - embedding/indexing flow
  - retrieval and traceability patterns

This project must treat Word and Excel as structured or semi-structured sources, not as flat text blobs.

The ingestion pipeline in this project must be specifically designed for Word and Excel formats.

---

## Architecture Principles

1. Separation of concerns
   - loaders → file reading
   - parsers → structure extraction
   - chunkers → chunk creation
   - embeddings → vector generation
   - retrieval → search logic
   - prompts → LLM interaction
   - app → orchestration

2. Reuse patterns, not implementation
   - use IFULLMDEV as a design reference
   - adapt for RFP-specific workflows and file types

3. Keep modules simple and testable
   - avoid large monolithic scripts
   - prefer small, composable functions

4. Traceability is required
   - every retrieved or generated answer must be traceable to source content

5. Preserve source structure wherever possible
   - headings, tables, sheet names, row context, and document sections should not be discarded early

---

## Data Model

The system must support the following entities.

### RFP Question
- question_text
- section
- subsection
- source_rfp
- customer
- date
- source_file

### RFP Answer
- answer_text
- linked_question
- source_document
- customer
- date
- reusable_flag
- approval_status
- won_lost_status
- source_file

### Supporting Reference Content
- title
- body_text
- source_document
- document_type
- product_or_service_area
- region
- date
- source_file

### Metadata for All Chunks
- source_file
- file_type
- document_type
- sheet_name (if Excel)
- heading_path (if Word)
- customer
- date
- product_or_service_area
- region
- chunk_type
- approval_status
- reusable_flag

---

## Ingestion Requirements

Support:
- Word (.docx)
- Excel (.xlsx)

The ingestion pipeline should produce:
1. raw extracted content
2. structured intermediate representation
3. chunked output with metadata
4. embedding-ready text

---

## Word Ingestion Strategy

Word documents should be parsed using document structure.

Required behavior:
- extract headings and heading hierarchy
- preserve section titles as metadata
- detect question/answer blocks where possible
- preserve tables when useful
- distinguish narrative sections from Q&A content

Preferred approach:
- chunk by heading section
- where possible, split by explicit question/answer pairs
- preserve parent-child heading path
- avoid arbitrary fixed-size chunking unless a section is too large

Examples of useful Word chunk units:
- one question with its answer
- one subsection containing a capability statement
- one policy or compliance statement section

If a section is too large:
- split by paragraph or subheading
- retain heading metadata on every resulting chunk

---

## Excel Ingestion Strategy

Excel files must be treated as structured data, not plain text.

Required behavior:
- read workbook, sheet names, columns, and rows
- preserve sheet-level context
- interpret each row as a record where appropriate
- convert structured row data into embedding-friendly text
- preserve original row values for traceability

Preferred approach:
- use row-based chunking as the baseline
- group rows only when they are strongly related
- enrich each row with:
  - workbook name
  - sheet name
  - column names
  - relevant surrounding context

Example:
A row should not be embedded as raw cell values only.
It should be transformed into meaningful text such as:
“This row from sheet ‘Security Responses’ in file ‘RFP_Answers_2024.xlsx’ contains a prior answer to a data security question covering encryption, access control, and audit logging.”

Excel chunking must preserve:
- sheet identity
- row identity where feasible
- field labels
- business meaning

---

## Chunking Strategy

### General Principles
- chunk by meaning, not by arbitrary size
- preserve source structure
- include metadata on every chunk
- avoid mixing unrelated topics in the same chunk

### Word
- chunk by section, subsection, or Q&A block
- heading hierarchy must be stored as metadata
- use paragraph-level fallback splitting only when necessary

### Excel
- chunk by row or tightly related row groups
- convert rows into enriched text before embedding
- store original structured values for audit and traceability

### Chunk Types
Possible chunk types include:
- question
- answer
- qa_pair
- capability_statement
- policy_statement
- reference_content
- spreadsheet_row
- spreadsheet_row_group

---

## Retrieval Requirements

Implement hybrid retrieval:
- semantic/vector search
- keyword/exact match retrieval

Support:
- filtering by metadata such as customer, product, document type, date, and approval status
- prioritising approved and reusable answers
- separating prior answers from supporting reference material

Retrieval should prefer:
1. approved reusable internal answers
2. approved supporting content
3. relevant historic answers needing review

---

## Prompting Rules

The system must support 3 modes.

### 1. Retrieve Only
- return relevant prior answers and supporting passages
- include source references
- do not generate a new answer unless asked

### 2. Grounded Answer
- synthesise an answer from retrieved content
- include references to the internal source material
- clearly separate retrieved evidence from generated synthesis

### 3. Draft Generation
- produce a polished RFP response
- use company tone where instructed
- clearly mark the output as DRAFT
- do not invent certifications, commitments, or capabilities

---

## Response Constraints

The system MUST:
- not invent certifications, claims, service levels, or capabilities
- prioritise internal retrieved content
- indicate uncertainty where evidence is weak
- distinguish between:
  - retrieved facts
  - inferred synthesis
  - draft wording

The system SHOULD:
- prefer approved wording over merely similar wording
- flag conflicting prior answers where detected
- highlight when human review is required

---

## Coding Standards

Language: Python

- use clear module structure
- use type hints where practical
- prefer dataclasses or simple models for structured records
- write readable, maintainable code
- avoid premature abstraction
- keep dependencies minimal unless justified

---

## Project Structure

Expected structure:

rfp_rag_assistant/
    loaders/
    parsers/
    chunkers/
    embeddings/
    retrieval/
    prompts/
    evaluation/
    app/
    config/
    tests/

Suggested responsibilities:
- loaders: file reading
- parsers: structure extraction from Word/Excel
- chunkers: convert parsed structures into chunks
- embeddings: embedding-ready transformations and indexing prep
- retrieval: hybrid search logic
- prompts: templates and orchestration
- evaluation: retrieval and answer quality checks
- app: top-level orchestration and entry points

---

## Logging and Observability

Log:
- files processed
- file type
- number of sections extracted
- number of rows extracted
- chunk counts
- embedding counts
- retrieval results
- sources used in generated responses
- warnings where parsing quality is poor

Word-specific logs should include:
- headings found
- sections extracted
- Q&A blocks detected

Excel-specific logs should include:
- workbook and sheet names
- rows processed
- missing or ambiguous columns
- row-to-text conversion statistics

---

## Evaluation

The system should support evaluation of:
- retrieval relevance
- answer grounding
- answer usefulness
- source traceability
- chunk quality

Evaluation should test Word and Excel ingestion separately because the parsing and chunking strategies differ.

---

## Constraints

- do not modify IFULLMDEV
- do not reuse PDF-specific parsing assumptions from IFULLMDEV
- do not flatten Word and Excel into generic text too early
- do not introduce unnecessary frameworks
- prefer clarity over abstraction

---

## Development Approach

Build incrementally.

### Phase 1
- Word and Excel ingestion
- metadata extraction
- chunking
- retrieval of prior answers and supporting content

### Phase 2
- grounded answer generation with source references

### Phase 3
- polished draft generation for RFP responses
- approval/reuse controls
- evaluation improvements

---

## Key Principle

This system is a:
- knowledge reuse engine
- retrieval assistant
- grounded response generation assistant

It is NOT:
- a regulatory analysis engine
- a PDF-first ingestion system

Focus on:
- reuse
- relevance
- source traceability
- practical response generation
