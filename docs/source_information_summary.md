# Source Information Summary

## Purpose

This note summarises the work completed so far to organise the available RFP source information for the `rfp_rag_assistant` prototype.

The aim of this work has been to:

- classify the available source documents
- understand the likely structure of the highest-value response documents
- identify embedded documents that should be treated as separate sources
- clarify which materials are immediately suitable for ingestion and chunking
- implement the first parser and chunker paths for the currently supported document types
- make the design rationale explicit by document classification, file type, and document shape

## Source Folder

Primary source folder reviewed:

- `/Users/frankbogle/Documents/RFP`

## Current Document Classifications

The source materials are currently organised into four operational classifications:

- `background_requirements`
- `combined_qa`
- `response_supporting_material`
- `tender_details`

### Intended Meaning Of Each Classification

`background_requirements`

- buyer-issued context, specifications, policies, requirements, contract material, and supporting annexes

`combined_qa`

- company response documents where the tender question and supplier answer are in the same file or are strongly implied to be paired

`response_supporting_material`

- company-issued supporting appendices and evidence provided alongside the formal answer documents

`tender_details`

- buyer-issued tender administration and procurement detail documents such as NDAs, evaluation information, call-off terms, and order forms

## File Types Present

### `background_requirements`

- `.docx`
- `.xlsx`
- `.pdf`

### `combined_qa`

- `.docx`

### `response_supporting_material`

- `.pdf`
- `.pptx`
- `.xlsx`

### `tender_details`

- `.docx`
- `.pdf`
- `.xlsx`

## Review Of `combined_qa`

The `combined_qa` folder appears to contain two main sub-patterns.

### 1. Strongly Structured ITT Files

Examples:

- `ITT01-Clinical Governance-Blatchford.docx`
- `ITT02-PSIRF-Blatchford.docx`
- `ITT03-Waiting List Management-Blatchford.docx`
- through `ITT19 ...`

Observed characteristics:

- a leading table is present
- the table usually contains fields such as:
  - `Question number`
  - `Detailed Question`
  - `Question`
  - `Character Count`
- the question text is explicitly present
- the remainder of the document appears to contain the supplier response

Implication:

- these files are strong candidates for deterministic `qa_pair` extraction

### 2. Earlier 1.x / 2.x Narrative Response Files

Examples:

- `1.2 GDPR.docx`
- `2.1 CONCISE SUMMARY Final.docx`
- `2.2 CONTRACTS AND FEEDBACK Final.docx`
- `2.3.x ...`

Observed characteristics:

- some include explicit `Response` labels
- some use tables with a heading plus response narrative
- some are clearly response-led but do not expose the question as cleanly as the ITT files

Implication:

- some will still support `qa_pair` extraction
- others may need a hybrid strategy where the answer is chunked as a response section tied to a question identifier from filename or local context

## Embedded Document Review

Embedded documents were scanned across the Office formats in the four classified folders.

### Classifications With Embedded Documents

- `background_requirements`
- `response_supporting_material`

### Classifications Without Embedded Documents Found

- `combined_qa`
- `tender_details`

### Files With Embedded Documents

#### `background_requirements`

- `Background info - SWS v4.docx`
  - embedded Excel workbook
- `Background information - Wheelchair and Specialist Seating Service.docx`
  - embedded Excel workbook
- `Wheelchair and Specialist Seating Service Specification.docx`
  - multiple embedded Word documents
  - one embedded Excel workbook

#### `response_supporting_material`

- `2.3.4_Appendix_Blatchford_Org_Chart.pptx`
  - embedded OLE object (`.bin`)

## Embedded Document Extraction

Embedded files have been extracted as copies only. The original source files were not modified.

Extraction folder:

- `/Users/frankbogle/Documents/RFP/extracted_embedded`

The extracted files are organised by:

- classification
- source document

Example structure:

- `extracted_embedded/background_requirements/...`
- `extracted_embedded/response_supporting_material/...`

### Extracted Embedded Files Suitable For Ingestion

Supported for further review and likely ingestion:

- embedded `.docx`
- embedded `.xlsx`

Current extracted supported items:

- Excel workbooks extracted from:
  - `Background info - SWS v4.docx`
  - `Background information - Wheelchair and Specialist Seating Service.docx`
  - `Wheelchair and Specialist Seating Service Specification.docx`
- multiple Word documents extracted from:
  - `Wheelchair and Specialist Seating Service Specification.docx`

### Extracted Embedded Files Not Currently Supported

- `oleObject1.bin`
  - source: `response_supporting_material/2.3.4_Appendix_Blatchford_Org_Chart.pptx`

Recommended treatment:

- retain for audit/reference
- do not include in the current ingestion and chunking pipeline

## Immediate Design Implications

### Retrieval Priority

For normal RFP response generation and evidence retrieval, the current working priority should be:

1. `combined_qa`
2. `response_supporting_material`
3. `background_requirements`
4. `tender_details`

### Chunking Implications

`combined_qa`

- preferred unit: `qa_pair`
- use deterministic extraction for the structured ITT files
- use hybrid response-section extraction for the earlier narrative files where question boundaries are weaker

`response_supporting_material`

- treat as supporting reference material
- chunk by section, heading, or worksheet row depending on file type

`background_requirements`

- treat as buyer-issued requirements and context
- chunk by heading, numbered clause, bullet group, and meaningful table block

`tender_details`

- ingest separately and rank down for normal service-answer retrieval
- retain for compliance, submission, and procurement-process queries

### Embedded Materials

- embedded `.docx` and `.xlsx` should be treated as separate source documents after review and classification
- embedded documents should not be merged inline with the parent document during chunking

## Parser And Chunker Implementation Status

The prototype now includes implemented parser and chunker paths for all four classifications, with support varying by file type.

### Implemented Parsers

- `combined_qa`
  - `ITTCombinedQAParser`
  - target: strongly structured `ITTxx` Word files
- `background_requirements`
  - `BackgroundRequirementsParser`
  - target: Word `.docx`
- `response_supporting_material`
  - `ResponseSupportingMaterialParser`
  - delegates to:
    - `ResponseSupportingMaterialExcelParser` for `.xlsx`
    - `PDFSectionParser` for `.pdf`
- `tender_details`
  - `TenderDetailsParser`
  - delegates to:
    - `BackgroundRequirementsParser` pattern for `.docx`
    - `ResponseSupportingMaterialExcelParser` pattern for `.xlsx`
    - `PDFSectionParser` for `.pdf`

### Implemented Chunkers

- `ITTCombinedQAChunker`
- `BackgroundRequirementsChunker`
- `ResponseSupportingMaterialChunker`
- `TenderDetailsChunker`

### Shared Chunking Utility

- `TextSplitter`
  - paragraph-first splitting
  - sentence fallback splitting
  - token-window fallback splitting
  - overlap handling

## Design Rationale By Classification And File Shape

The parser and chunker design has been driven by actual document shape rather than a single generic ingestion rule.

### `combined_qa`

#### Primary File Shape

- structured Word `.docx`
- leading metadata/question table
- explicit question text
- answer narrative following `Response`

#### Parser Design Rationale

- use deterministic extraction where the structure is explicit
- read the first table to extract:
  - `question_id`
  - `question_title`
  - `question_text`
- capture answer text from the table and following body paragraphs

This design was chosen because the `ITTxx` files expose a strong and repeatable Q&A pattern.

#### Chunker Design Rationale

- chunk by answer content while preserving the full question on every chunk
- output is effectively a `qa_pair` chunk stream
- use token splitting only when the answer is too large

This design supports future answer reuse and retrieval because the chunk always retains the question context.

### `background_requirements`

#### Primary File Shape

- buyer-issued Word `.docx`
- mixed heading quality
- explicit paragraph styles in some files
- bold standalone headings in others
- numbered sections, bullets, and tables

#### Parser Design Rationale

- use heading styles first
- fall back to bold standalone heading detection
- preserve heading hierarchy
- convert tables into text rows rather than dropping them

This design was chosen because the real files show meaningful section structure, but not always with perfectly consistent styling.

#### Chunker Design Rationale

- chunk by section
- preserve:
  - `heading_path`
  - section title
  - section traceability
- only split within a section when token limits require it

This fits buyer-issued requirement/context documents, where the section is the natural retrieval unit.

### `response_supporting_material`

#### Primary File Shape

- mostly `.pdf`
- one significant `.xlsx`
- evidence and policy material rather than direct Q&A

#### Parser Design Rationale

For `.xlsx`:

- detect usable header rows
- emit row-level parsed sections where possible
- fall back to sheet summaries for non-tabular sheets

For `.pdf`:

- extract page text
- strip repeated page headers/footers
- detect numbered or heading-like section lines
- merge obvious layout artifacts back into parent sections

This design was chosen because the classification contains mixed evidence material rather than a single document pattern.

#### Chunker Design Rationale

- preserve spreadsheet-specific metadata when present:
  - `sheet_name`
  - `row_index`
- otherwise chunk as reference sections
- do not force Q&A semantics onto supporting evidence

This keeps the material useful for grounding while preserving file-type-specific traceability.

### `tender_details`

#### Primary File Shape

- mixed `.docx`, `.xlsx`, and `.pdf`
- tender instructions, order forms, evaluation matrices, administrative content

#### Parser Design Rationale

The parser dispatches by file type:

- `.docx`
  - section-based parsing similar to `background_requirements`
- `.xlsx`
  - row/sheet parsing similar to `response_supporting_material`
- `.pdf`
  - section-based parsing using `PDFSectionParser`

This design was chosen because tender details are structurally mixed but conceptually unified as procurement/admin content.

#### Chunker Design Rationale

- preserve heading path for Word/PDF
- preserve `sheet_name` and `row_index` for Excel
- treat content as reference/procurement material rather than reusable answer text

This allows the corpus to be queried when needed without letting tender admin content dominate service-answer retrieval.

## PDF Design Notes

The PDF path was inspired by the architectural shape of the `IFULLMDEV` project, but reimplemented for RFP use cases.

Useful patterns adapted:

- separate extraction, section mapping, and chunking stages
- preserve section identity and chunk ordering
- use cleanup passes to merge layout noise back into the parent section

Important adaptation:

- no IFU/device-specific metadata or taxonomy was copied
- the PDF parser here is RFP-oriented and still considered first-pass compared with the Word/Excel paths

## Section Title Handling

The prototype now keeps both:

- raw extracted section title
- normalized section title

Rationale:

- raw title preserves source fidelity and auditability
- normalized title gives cleaner downstream display and comparison

Examples:

- raw: `INTRODUCTION AND BACKGROUND`
  - normalized: `Introduction and Background`
- raw: `SECTION A – INSTRUCTIONS AND INFORMATION`
  - normalized: `Section A – Instructions and Information`

Normalized titles are stored alongside the raw title rather than replacing it.

## External URL Review And Ingestion Approach

External links found in the source corpus are now treated as a separate ingestion problem rather than being mixed directly with internal document chunks.

### Why External Links Matter

- some customer-issued RFP documents cite external guidance that appears to form part of the expected response context
- some prior company responses also cite external guidance or supporting publications
- these references can improve answer quality and alignment when they are clearly traceable and ranked appropriately

### Current Policy Decision

The current working rule is:

- include external links extracted from:
  - `.docx`
  - `.xlsx`
- exclude external links extracted from:
  - `.pdf`

Rationale:

- Word and Excel preserve links more reliably
- PDF-derived URLs are much more likely to be truncated or extraction artefacts
- excluding PDF-derived URLs reduces ingestion noise and avoids indexing broken references

### URL Filtering Stages

The external-reference review now follows these filtering stages:

1. extract candidate URLs from supported source files
2. remove Office/schema and XML namespace noise
3. remove obviously non-content links such as:
   - login pages
   - registration pages
   - procurement portals
4. classify the remaining URLs as:
   - `ingest`
   - `review`
   - `ignore`
5. retain provenance:
   - source classification
   - source file
   - source file type

### Current Review Heuristics

#### `ingest`

Public guidance, policy, standards, or reference sources that are likely to be useful for grounded answering, for example:

- NHS England
- NHS Digital
- GOV.UK
- EUR-Lex
- ICO
- PMG
- Wheelchair Managers Forum
- NHS SBS
- NICE
- legislation.gov.uk

#### `review`

Links that may be useful but need manual judgement, such as:

- internal SharePoint links
- supplier-owned marketing pages
- secondary professional or training sites
- sources that may be legitimate but are lower-confidence than core policy/guidance domains

#### `ignore`

Links that should not enter the external-reference corpus, such as:

- login or registration pages
- supplier portals
- procurement submission portals
- malformed or obviously broken URLs

### External Reference Parsing And Chunking Design

The external-reference ingestion path follows the same architectural principles as the rest of the system:

- loader
  - fetch approved HTML content
- parser
  - strip scripts, styles, navigation, footer, cookie-banner text, and obvious menu/listing sections
  - extract page title, headings, paragraphs, and lists
  - emit section-like `ParsedSection` objects
- chunker
  - chunk by section and paragraph group
  - enforce the existing token limit using the shared `TextSplitter`
  - attach source provenance on every chunk

### External Reference Metadata

External-reference chunks should carry, at minimum:

- `source_url`
- `source_domain`
- `reference_origin`
  - `customer_cited`
  - `supplier_cited`
- `referenced_from_file`
- `referenced_from_classification`
- `section_title`
- `section_title_normalized`

### Retrieval Implication

External references should not be treated as equivalent to internal answer material.

Recommended priority remains:

1. `combined_qa`
2. `response_supporting_material`
3. customer-cited `external_reference`
4. `background_requirements`
5. `tender_details`

This approach allows customer-cited external guidance to support answer grounding without displacing internal approved wording.

### Current HTML Parsing Status

The current HTML path is usable for curated references but still intentionally conservative:

- cookie banners are suppressed
- generic menu/listing blocks are suppressed
- promotional/event sections are suppressed where they are clearly non-content
- clean policy-style pages currently parse better than noisier association/news pages

This is sufficient for a reviewed allowlist of URLs, but not yet a general-purpose web crawler.

## Recommended Next Steps

1. Review the extracted embedded `.docx` and `.xlsx` files and classify them into the same document taxonomy.
2. Produce and maintain a reviewed URL inventory using only Word/Excel-derived external references.
3. Prioritise `customer_cited` external references for the first external corpus ingestion pass.
4. Wire the parsed and chunked outputs into the next layer:
   - embedding preparation
   - vector indexing
   - retrieval preview
5. Add chunking-run reporting so each ingestion run explains:
   - sections found
   - chunks created
   - split behavior
   - warnings

## Current Prototype Relevance

This source-organisation work directly supports the operational prototype by:

- defining the ingestion classes
- identifying the highest-value response corpus
- separating supporting and administrative material
- surfacing embedded documents that should become first-class input sources
- reducing the risk of overfitting chunking rules to the wrong document types
- proving that parser and chunker design should vary by document type and file shape rather than by one generic ingestion rule
- creating a usable end-to-end ingestion preview path for all four classifications across the currently supported file types
