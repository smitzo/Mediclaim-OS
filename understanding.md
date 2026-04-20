# Document Processor Technical Understanding

This document explains the project from an engineering point of view: what the system does, how the main modules interact, why this architecture was chosen, what tradeoffs were accepted, and how the project can be improved further.

## 1. Project Goal

The project processes medical insurance claim PDFs.

A single claim PDF can contain many mixed document pages:

- claim forms
- identity documents
- bank or cheque details
- itemized hospital bills
- discharge summaries
- prescriptions
- investigation reports
- payment receipts
- unrelated or unknown pages

The system converts that mixed PDF into one structured JSON response with:

- page classification
- extracted identity and policy details
- extracted discharge summary details
- extracted billing details
- processing errors
- processing metadata

The important product goal is not only extraction. The system also needs to handle many documents without blocking the API, losing visibility, or forcing the user to wait on one long HTTP request.

## 2. High-Level Architecture

The current architecture is:

```text
Next.js frontend
  -> FastAPI API
  -> file-backed durable storage
  -> Redis broker
  -> Celery worker
  -> LangGraph claim pipeline
  -> stored JSON result
  -> frontend polling and inspection
```

The frontend is an operator dashboard. It uploads files, lists jobs, shows status counts, and displays extraction results.

The backend exposes upload and status APIs. It validates PDFs, stores uploads, creates durable job records, and enqueues background work.

The worker executes the actual document-processing pipeline. That pipeline uses LangGraph to classify pages, route pages to specialist agents, and aggregate the final output.

## 3. Why Background Jobs Were Chosen

The older synchronous model was:

```text
POST /api/process
  -> keep request open
  -> process the full PDF
  -> return final JSON
```

That model is easy to demo but weak for real claim processing.

Problems with the synchronous model:

- HTTP requests can time out before processing completes.
- API workers are occupied by slow CPU, OCR, PDF, and LLM work.
- A server restart loses the in-flight request.
- The user cannot track many PDFs at once.
- Retry, observability, and partial failure handling are harder.
- Scaling the API also accidentally scales heavy processing, even if only workers need more capacity.

The asynchronous model is:

```text
POST /api/claims/batch
  -> validate files
  -> store uploads
  -> create job records
  -> enqueue job IDs
  -> return quickly

Celery worker
  -> read one job
  -> process PDF
  -> save result
  -> update status
```

This approach was chosen because document extraction is naturally a long-running workflow. The API should be fast and predictable; the worker should absorb the slow work.

Why not only use the synchronous endpoint?

- It is acceptable for a small assignment demo.
- It is not reliable for batches, high page counts, retries, or production load.
- It couples user experience to backend processing time.

Why not use WebSockets immediately?

- Polling is simpler and good enough for a job dashboard.
- Job status changes are low frequency.
- WebSockets add connection lifecycle concerns, auth concerns, and infrastructure complexity.
- WebSockets can be added later without changing the core job model.

## 4. Frontend Design

Frontend files live under:

```text
frontend/
```

Key files:

```text
frontend/app/page.tsx
frontend/lib/api.ts
frontend/lib/demo-data.ts
```

`page.tsx` is the main dashboard.

It contains:

- batch upload controls
- job statistics
- recent job table
- demo data controls
- result summary
- raw JSON inspector

`api.ts` contains typed API helpers:

- `listJobs()`
- `submitClaims()`
- `getClaimResult()`

This separation is intentional. React components should not know every URL and parsing rule. If the backend URL changes, the API client can change in one place.

`demo-data.ts` contains deterministic demo jobs and outputs. The demo uses the same TypeScript types as the live API:

- `ClaimJob`
- `ClaimResponse`

That matters because the demo does not create a separate fake UI path. It exercises the same dashboard rendering logic used by real backend results.

## 5. Why Demo Data Is Frontend-Local

The demo data was added in the frontend instead of the backend.

This was chosen because the request was to show sample outputs from the UI. Frontend-local demo data has several practical benefits:

- no database setup is required
- no Redis setup is required
- no worker setup is required
- demos work offline
- screenshots and walkthroughs are deterministic
- the real backend API remains clean

Why not seed the backend storage directly?

- File-backed storage is implementation-specific.
- Seeding backend files would mix demo artifacts with real job state.
- It would require users to know where `DATA_DIR` points.
- It would not help when the frontend is reviewed independently.

Why not make the demo data completely separate from real types?

- Separate demo shapes often drift from real API contracts.
- Using the same types gives compile-time feedback when the API model changes.
- It makes the demo useful as a lightweight contract example.

## 6. Backend API Layer

The backend route definitions are in:

```text
app/api/routes.py
```

Important endpoints:

```text
POST /api/process
POST /api/claims
POST /api/claims/batch
GET /api/claims
GET /api/claims/{job_id}
GET /api/claims/{job_id}/result
```

`POST /api/process` is kept for compatibility. It processes one uploaded PDF synchronously and returns the final response.

The preferred flow is:

```text
POST /api/claims/batch
GET /api/claims
GET /api/claims/{job_id}/result
```

The batch endpoint accepts many files and returns job metadata. Rejected files are reported individually, so one bad PDF does not have to reject the whole batch.

## 7. Validation Strategy

Upload validation checks:

- file name exists
- file extension is `.pdf`
- file is not empty
- file size is under the configured limit
- PyMuPDF can open the file
- page count is under the configured limit

The validation logic protects the system from:

- non-PDF uploads
- corrupted files
- huge files
- PDFs with too many pages
- expensive inputs that could exhaust worker memory

Why validate before creating a job?

- Invalid files should not enter the queue.
- Workers should spend time on processable jobs.
- Users should get quick feedback for rejected files.

Why not trust browser-side validation?

- Browser validation can be bypassed.
- API validation is the real security and reliability boundary.

## 8. Storage Boundary

Storage code lives in:

```text
app/services/storage.py
```

Current storage uses local files:

```text
data/
  uploads/
  jobs/
  results/
```

The storage layer saves:

- uploaded PDF bytes
- job metadata JSON
- final result JSON

This file-backed approach was chosen for local development and assignment review because it is easy to run without a database.

The important design choice is the boundary, not the file format. Other modules call `ClaimStorage` instead of manually writing random files. That makes a future migration easier.

Production replacement options:

- uploaded PDFs in S3, GCS, or Azure Blob Storage
- job metadata in PostgreSQL
- final JSON results in PostgreSQL or object storage
- job status indexed by claim ID, user ID, tenant ID, and creation date

Why not start with PostgreSQL immediately?

- It adds setup cost.
- The MVP does not need complex querying yet.
- The storage abstraction keeps the migration path open.

Why not store PDFs in the database?

- Large binary objects make database backup and replication heavier.
- Object storage is cheaper and better suited for file payloads.
- Databases are better for metadata, indexing, audit trails, and status.

## 9. Queue And Worker Layer

Celery is used for background execution.

Files:

```text
app/workers/celery_app.py
app/workers/tasks.py
```

Redis is used as:

- Celery broker
- Celery result backend

Docker Compose starts Redis, the API, and the worker together.

Why Celery?

- It is a proven Python task queue.
- It supports worker concurrency, retries, time limits, and separate worker processes.
- It lets the API remain responsive while workers process PDFs.

Why Redis?

- It is simple to run locally.
- It is fast enough for queue broker workloads.
- It works well with Celery.

Why not run processing in FastAPI background tasks?

- FastAPI background tasks still live inside the API process.
- They are not durable enough for serious queue workloads.
- They make worker scaling and retry control weaker.
- A process restart can interrupt work without the same queue semantics.

Why not use Kafka?

- Kafka is excellent for event streaming, but heavier than needed here.
- This project needs task dispatch, not a full event log.
- Celery plus Redis is a better MVP tradeoff.

## 10. Pipeline Orchestration With LangGraph

The graph is defined in:

```text
app/core/graph.py
```

Conceptual graph:

```text
Segregator
  -> ID Agent
  -> Discharge Agent
  -> Bill Agent
  -> Aggregator
```

The shared state model is `ClaimState` in:

```text
app/core/schemas.py
```

LangGraph is useful because the pipeline has multiple stateful steps:

- classify pages
- create a document type to page map
- route pages to different extractors
- merge multiple agent outputs
- preserve errors
- produce a final response

Why LangGraph instead of plain function calls?

- Plain function calls work for a tiny pipeline.
- LangGraph gives a clearer execution model for multi-step agent workflows.
- State transitions are explicit.
- Parallel or conditional routing can be added more naturally.
- The graph structure documents the pipeline shape.

Why not one giant agent prompt?

- One prompt over the entire PDF is harder to debug.
- It can waste context on irrelevant pages.
- Billing, identity, and clinical extraction have different schemas.
- Smaller specialist agents reduce prompt complexity and can fail independently.

## 11. Page Classification

The segregator lives in:

```text
app/agents/segregator.py
```

It classifies pages into:

```text
claim_forms
cheque_or_bank_details
identity_document
itemized_bill
discharge_summary
prescription
investigation_report
cash_receipt
other
```

The project uses a text-first strategy:

1. Extract text from the PDF page.
2. Apply local keyword and structure heuristics.
3. Use the LLM only when needed.
4. Render page images lazily for visual fallback.

This matters because many hospital bills and forms are text-based PDFs. Rendering every page to an image would be slower and more memory intensive.

Why text-first?

- Text is smaller than images.
- Text extraction is faster than image rendering.
- Text-only LLM prompts are cheaper than vision prompts.
- Deterministic heuristics are easier to debug.

Why not always use OCR?

- OCR is useful for scanned pages.
- OCR is unnecessary for digital PDFs with embedded text.
- OCR adds latency and can introduce recognition errors.

Why not always use vision LLM calls?

- Vision calls are slower and more expensive.
- They add rate-limit risk.
- They can be unnecessary for clean text PDFs.
- They make large batch processing less predictable.

## 12. Page Routing

After classification, the pipeline creates a document page map:

```text
document_type -> list of page indexes
```

Routing rules are defined in `AGENT_DOCUMENT_MAP`:

```text
identity_document -> id_agent
claim_forms -> id_agent
cheque_or_bank_details -> id_agent
discharge_summary -> discharge_agent
prescription -> discharge_agent
itemized_bill -> bill_agent
cash_receipt -> bill_agent
investigation_report -> bill_agent
other -> id_agent
```

This design avoids sending the full PDF to every agent.

Benefits:

- lower token usage
- lower image rendering cost
- better extraction focus
- easier debugging
- smaller blast radius when one document type is classified incorrectly

Why route pages instead of asking each agent to search the full PDF?

- Searching the full PDF duplicates work.
- Agents can be distracted by unrelated pages.
- Large PDFs can exceed model context limits.
- Per-agent inputs are easier to test.

## 13. Extraction Agents

The extraction agents are:

```text
app/agents/id_agent.py
app/agents/discharge_agent.py
app/agents/bill_agent.py
```

The ID agent extracts:

- patient name
- date of birth
- gender
- contact information
- policy number
- insurance provider
- identity number
- bank details

The discharge agent extracts:

- admission date
- discharge date
- diagnosis
- hospital name
- physician
- treatment summary
- discharge medication
- follow-up instructions

The bill agent extracts:

- bill number
- bill date
- hospital name
- line items
- subtotal
- tax
- discount
- insurance payment
- total amount
- patient responsibility

The agents use schema-oriented outputs defined in:

```text
app/core/schemas.py
```

Why use Pydantic schemas?

- They make the output contract explicit.
- They support validation and serialization.
- They make the API response predictable.
- They help frontend TypeScript types mirror backend shapes.

Why keep `extra_fields`?

- Real medical documents vary a lot.
- Some useful fields are not known in advance.
- `extra_fields` preserves additional information without breaking the schema.

The tradeoff is that `extra_fields` must be monitored. If the same field appears often, it should graduate into the formal schema.

## 14. Aggregation

The aggregator is in:

```text
app/agents/aggregator.py
```

It combines:

- page classifications
- identity extraction
- discharge extraction
- billing extraction
- unique errors
- processing summary

The final response model is:

```text
ClaimResponse
```

The aggregator sets status as:

- `success` when extraction succeeds without errors
- `partial` when some data exists but errors occurred
- `failed` when no meaningful extraction exists

Why aggregate at the end?

- It creates a single stable API response.
- It avoids leaking internal graph state to clients.
- It allows each agent to evolve independently.
- It centralizes final status logic.

## 15. Error Handling Strategy

The system distinguishes job status from response status.

Job status:

```text
queued
processing
succeeded
partial
failed
```

Response status:

```text
success
partial
failed
```

The job status is for the queue and dashboard. The response status is for the extraction result itself.

The pipeline collects errors instead of immediately throwing for every recoverable issue. That supports partial outputs, which are important in document processing. A single unreadable prescription page should not discard the extracted identity and bill data.

Why allow partial results?

- Real PDFs are messy.
- Some pages may be scanned poorly.
- Users still need usable extracted data.
- Review workflows can resolve missing fields manually.

## 16. Frontend Result Display

The frontend now shows:

- status metrics
- a job table
- demo controls
- a structured result summary
- raw JSON

The structured result summary is for quick human scanning. The raw JSON remains useful for developers and API reviewers.

Why keep raw JSON?

- It exposes the exact API response.
- It helps validate schemas quickly.
- It makes demo output transparent.
- It is useful when adding new fields.

Why not only show raw JSON?

- Operators need fast summaries.
- Claim review usually starts with patient, policy, diagnosis, and total amount.
- A visual summary reduces cognitive load.

## 17. Configuration

Important configuration lives in:

```text
app/core/config.py
```

Examples:

```text
GOOGLE_API_KEY
DATA_DIR
MAX_UPLOAD_BYTES
MAX_PDF_PAGES
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
TASK_TIME_LIMIT_SECONDS
```

Configuration is externalized so different environments can change behavior without editing code.

Why environment variables?

- They work well in Docker and cloud platforms.
- They keep secrets out of source code.
- They let production limits differ from development limits.

## 18. Current Strengths

The project already has several good architecture choices:

- asynchronous job processing
- batch upload support
- explicit schemas
- storage abstraction
- worker/API separation
- page-level classification
- specialist extraction agents
- text-first optimization
- lazy image rendering
- partial result support
- frontend polling dashboard
- deterministic demo data

These choices make the project more realistic than a one-endpoint PDF demo.

## 19. Current Limitations

The project is still an MVP.

Important limitations:

- local file storage is not ideal for multi-server production
- no authentication or tenant isolation
- no role-based access control
- no database indexes for searching jobs
- no manual review workflow
- no confidence score normalization across all fields
- limited observability beyond logs
- no automated frontend tests yet
- no golden dataset evaluation for extraction quality
- no PII redaction policy
- no audit trail for who viewed or changed a claim

These are not failures. They are normal next steps when moving from assignment-quality architecture toward production.

## 20. Recommended Improvements

### 20.1 Storage And Data Model

Move job metadata to PostgreSQL.

Useful tables:

- claims
- claim_jobs
- claim_documents
- claim_results
- extraction_errors
- audit_events

Store PDF files in object storage with signed URLs.

Benefits:

- better querying
- better durability
- safer multi-instance deployment
- retention policies
- easier audit trails

### 20.2 Authentication And Authorization

Add authentication before exposing real medical documents.

Recommended controls:

- user login
- organization or tenant ID
- role-based permissions
- access logging
- per-claim authorization checks

Medical claim data is sensitive. Access control should be treated as a core feature before production use.

### 20.3 Human Review Workflow

Add a review screen where operators can:

- compare extracted values with source pages
- edit incorrect fields
- mark confidence issues
- approve or reject extracted output
- export a reviewed final JSON

This is important because AI extraction should usually be reviewed before financial or insurance decisions.

### 20.4 Better Field Confidence

The current page classification has confidence, but field-level confidence should be added.

Example:

```json
{
  "patient_name": {
    "value": "Aarya Mehta",
    "confidence": 0.96,
    "source_pages": [1],
    "source_text": "Patient Name: Aarya Mehta"
  }
}
```

This improves review, auditing, and downstream trust.

### 20.5 Source Citations

Each extracted field should reference where it came from:

- page number
- bounding box if OCR is available
- source snippet
- extraction method

This allows reviewers to verify outputs quickly.

### 20.6 Evaluation Dataset

Create a small private test dataset:

- 20 clean digital PDFs
- 20 scanned PDFs
- 20 mixed-quality PDFs
- expected JSON outputs

Then run regression tests after prompt, heuristic, or parser changes.

Track metrics:

- page classification accuracy
- field extraction precision
- field extraction recall
- total processing time
- LLM cost per claim
- partial failure rate

### 20.7 Observability

Add structured logging and metrics.

Useful metrics:

- jobs queued
- jobs processing
- jobs failed
- average processing time
- average pages per claim
- LLM calls per claim
- token usage
- PDF rendering time
- extraction errors by agent

Recommended tools:

- OpenTelemetry
- Prometheus
- Grafana
- Sentry

### 20.8 Queue Robustness

Improve background processing with:

- retries for transient failures
- dead-letter handling
- idempotent task execution
- worker concurrency tuning
- per-job timeout policies
- queue priority for urgent claims

Idempotency matters because a worker may retry a job after failure. Saving results should not corrupt the job if the same task runs twice.

### 20.9 Frontend Improvements

Useful frontend next steps:

- filter jobs by status
- search by claim ID or filename
- show upload progress
- add pagination
- add field-level result tabs
- add side-by-side document preview
- add manual correction forms
- export result JSON
- compare original and reviewed output

The current dashboard is a good operator starting point, but a production workflow needs review and correction.

### 20.10 Security And Compliance

Before real medical data is used:

- encrypt stored PDFs
- encrypt database volumes
- redact sensitive logs
- avoid logging extracted PII
- enforce HTTPS
- rotate secrets
- define retention policies
- add audit logs
- document data deletion behavior

Medical claims often contain personal, financial, and clinical information. Security cannot be left as a deployment detail.

## 21. Summary

This project is designed around a practical document-processing architecture.

The key technical idea is separation of responsibilities:

- the frontend manages operator interaction
- the API validates and creates jobs
- storage preserves uploads and results
- the queue decouples slow processing from HTTP requests
- workers run expensive extraction
- LangGraph coordinates multi-agent document understanding
- schemas define stable contracts
- aggregation returns one consistent result

The chosen approach is more complex than a single endpoint, but that complexity solves real problems: long-running processing, batching, failures, scaling, and result visibility.

The next major step is not another extraction prompt. The next major step is making the system reviewable, measurable, secure, and production-durable.
