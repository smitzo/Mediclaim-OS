# Document Processor System Design

## 1. System Purpose

The system processes medical insurance claim PDFs for multiple companies.

Each company is a tenant. A tenant uploads claim PDFs, monitors background processing jobs, and reviews extracted claim outputs. Tenant data must remain isolated from other tenants.

The project currently demonstrates this through a frontend company registration/sign-in flow, tenant-aware API calls, demo tenant bypass credentials, and deterministic demo data. In a production system, the same concepts should be enforced in the backend, database, object storage, queue workers, and observability pipeline.

## 2. Core Requirements

Functional requirements:

- company registration
- company sign-in
- demo bypass login with username `demo` and password `demo`
- batch PDF upload
- background claim processing
- job status tracking
- structured result inspection
- JSON export
- demo data for 50 customer claims
- tenant-aware dashboard behavior

Non-functional requirements:

- reliable background processing
- tenant isolation
- scalable batch throughput
- durable storage of uploads and results
- retryable worker execution
- secure handling of medical and financial data
- observable failures and performance bottlenecks

## 3. High-Level Architecture

```text
Browser
  -> Next.js frontend
  -> API gateway / load balancer
  -> FastAPI API service
  -> PostgreSQL metadata database
  -> Object storage for PDFs and result artifacts
  -> Redis or managed broker
  -> Celery worker pool
  -> LangGraph extraction pipeline
  -> LLM / OCR / PDF services
```

The current repo uses local file storage and Redis/Celery because it is simple to run locally. The production architecture should preserve the same boundaries while replacing local files with managed durable services.

## 4. Multi-Tenant Model

Every company should have a tenant record.

Recommended tenant fields:

```text
tenant_id
company_name
status
plan
created_at
updated_at
```

Every user belongs to one or more tenants.

Recommended user fields:

```text
user_id
tenant_id
email_or_username
password_hash
role
created_at
last_login_at
```

Every claim job must include `tenant_id`.

Recommended claim job fields:

```text
job_id
tenant_id
claim_id
filename
status
page_count
file_size_bytes
upload_object_key
result_object_key
error
created_at
updated_at
```

The key rule is simple: every query, upload, result read, and worker update must be scoped by `tenant_id`.

## 5. Authentication And Authorization

The frontend now demonstrates:

- company registration
- company sign-in
- session persistence
- demo bypass with `demo` / `demo`
- tenant ID propagation through API request headers

For production, this should move to backend-enforced auth:

- store passwords with a slow hash such as Argon2 or bcrypt
- issue signed HTTP-only session cookies or JWTs
- attach `tenant_id` and role claims to the authenticated principal
- reject requests where the user cannot access the requested tenant
- never trust tenant IDs only because the browser sends a header

The `X-Tenant-ID` header is useful as a routing hint, but backend authorization must derive the trusted tenant from the authenticated session.

## 6. Tenant Isolation Strategy

Recommended isolation layers:

- API: every route reads the authenticated tenant and scopes queries.
- Database: every tenant-owned table has `tenant_id`.
- Object storage: object keys include tenant prefixes, such as `tenants/{tenant_id}/uploads/{job_id}.pdf`.
- Queue messages: task payloads include both `tenant_id` and `job_id`.
- Worker: workers load and update jobs by `(tenant_id, job_id)`, not only `job_id`.
- Logs: logs include tenant IDs for debugging, but avoid logging PII.
- Metrics: metrics can include tenant-level aggregation where safe.

For stronger enterprise isolation, high-value tenants can later move to dedicated databases, buckets, or worker queues.

## 7. Request Flow

### 7.1 Company Sign-In

```text
User enters credentials
  -> API validates credentials
  -> API creates session
  -> frontend receives authenticated tenant context
  -> dashboard loads tenant-scoped jobs
```

The current demo performs this in browser storage. That is acceptable for a local demo, but not for production.

### 7.2 Batch Upload

```text
Frontend sends PDFs with tenant context
  -> API authenticates request
  -> API validates each PDF
  -> API stores PDFs in object storage
  -> API creates job rows in PostgreSQL
  -> API enqueues one task per job
  -> frontend receives accepted and rejected files
```

Rejected files should not block accepted files. This is important for large batches where one corrupted PDF should not fail the whole upload.

### 7.3 Worker Processing

```text
Worker receives tenant_id and job_id
  -> marks job processing
  -> reads PDF from object storage
  -> runs LangGraph pipeline
  -> writes structured JSON result
  -> marks job succeeded, partial, or failed
```

The worker must be idempotent. If the queue retries the same job, the worker should not create duplicate claims or corrupt a completed result.

## 8. Data Storage Design

Use PostgreSQL for metadata:

- tenants
- users
- claim_jobs
- claim_results
- extraction_errors
- audit_events

Use object storage for:

- original PDFs
- rendered page images when needed
- large OCR artifacts
- final JSON result documents if they are large

Why this split?

- databases are best for indexing, filtering, status, and relationships
- object storage is best for large binary documents
- backup and retention policies can differ by data type

## 9. Queue And Scaling Design

Celery workers can scale horizontally.

Scaling levers:

- increase API replicas for more concurrent uploads
- increase worker replicas for more processing throughput
- split queues by priority or tenant plan
- separate heavy scanned-PDF workloads from text-based PDF workloads
- tune worker concurrency based on CPU, memory, and LLM rate limits

Example queues:

```text
claims.default
claims.priority
claims.ocr-heavy
claims.retry
```

This prevents expensive OCR-heavy jobs from starving normal text-based jobs.

## 10. Reliability Design

Important reliability patterns:

- durable job rows before queue publish
- task acknowledgement after processing
- retries for transient failures
- dead-letter queue for repeated failures
- idempotent result writes
- per-job timeout
- status transitions with timestamps
- partial result support

Recommended status flow:

```text
queued -> processing -> succeeded
queued -> processing -> partial
queued -> processing -> failed
processing -> queued       retry path
failed -> queued           manual retry path
```

Partial results are important. Medical claim PDFs are messy, and a single bad prescription page should not discard extracted identity and billing data.

## 11. LangGraph Pipeline Design

Pipeline shape:

```text
Segregator
  -> ID Agent
  -> Discharge Agent
  -> Bill Agent
  -> Aggregator
```

The segregator classifies pages first. Specialist agents then process only relevant pages. This improves cost, accuracy, and latency because each agent receives a smaller focused input.

The aggregator produces one stable API response:

```text
claim_id
status
page_classification
extracted_data
errors
processing_summary
```

## 12. Performance Strategy

Major performance choices:

- text extraction before image rendering
- heuristic classification before LLM calls
- lazy page rendering
- page routing to specialist agents
- chunked processing for long bills
- background workers instead of blocking HTTP requests
- result polling instead of always-open connections

For very large workloads, add:

- OCR cache by PDF hash
- LLM response cache for repeated pages
- worker autoscaling based on queue depth
- tenant-level rate limits
- batch size limits

## 13. Security Design

Production security requirements:

- HTTPS everywhere
- server-side authentication
- password hashing
- signed sessions
- tenant-scoped authorization checks
- encryption at rest for database and object storage
- object storage private by default
- signed URLs only when needed
- PII redaction in logs
- audit events for viewing and exporting claims
- retention and deletion policies

Medical claims can contain identity, financial, and clinical data. Logging raw extracted data should be avoided unless explicitly required and protected.

## 14. Observability

Useful logs:

- job accepted
- job rejected
- job started
- page classification completed
- agent completed
- result saved
- job failed

Useful metrics:

- upload count by tenant
- rejected upload count
- queue depth
- worker processing time
- extraction success rate
- partial result rate
- failure rate by agent
- LLM calls per claim
- average cost per claim

Useful traces:

- upload request
- storage write
- queue publish
- worker execution
- PDF parsing
- agent calls
- result write

Recommended tools:

- OpenTelemetry
- Prometheus
- Grafana
- Sentry

## 15. API Design Direction

Recommended production API:

```text
POST /api/auth/register-company
POST /api/auth/sign-in
POST /api/auth/sign-out
GET  /api/me

POST /api/claims/batch
GET  /api/claims
GET  /api/claims/{job_id}
GET  /api/claims/{job_id}/result
POST /api/claims/{job_id}/retry
```

The API should not expose jobs from other tenants. Every route should resolve tenant context from the authenticated session.

## 16. Frontend Design Direction

The dashboard should evolve into tenant-aware operational software:

- company registration and login
- tenant name and tenant ID display
- job filters
- upload progress
- result tabs
- JSON export
- manual review workflow
- field correction forms
- source page preview
- audit history

The current UI demonstrates the first tenant-aware step while keeping the project easy to run locally.

## 17. Why This Architecture Is Scalable

The architecture scales because each heavy part can grow independently:

- API replicas handle more uploads and reads.
- Worker replicas handle more processing.
- Object storage handles large PDFs cheaply.
- PostgreSQL handles metadata and indexing.
- Redis or a managed broker buffers workload spikes.
- LLM calls are isolated behind agent utilities.

The API does not need to stay busy while PDFs process. Workers can be added when queue depth grows.

## 18. Why This Architecture Is Reliable

The architecture is reliable because:

- accepted uploads are stored before processing starts
- jobs have durable status records
- workers can retry jobs
- failures are isolated per claim
- partial results preserve useful extracted data
- users can reload the dashboard and still see job state
- result artifacts are saved independently of the browser session

This is the main advantage over a single synchronous upload endpoint.

## 19. Future Production Roadmap

Recommended order:

1. Move auth from browser storage to backend sessions.
2. Add PostgreSQL tenant, user, and job tables.
3. Move PDFs and result artifacts to object storage.
4. Enforce tenant checks in every API route.
5. Add worker idempotency and retry policies.
6. Add audit logging for claim views and exports.
7. Add field-level confidence and source citations.
8. Add human review and correction screens.
9. Add evaluation datasets and extraction quality metrics.
10. Add autoscaling and queue priority policies.

## 20. Summary

The system should be treated as a tenant-scoped document processing platform.

The scalable design is not one large server doing everything. It is a set of clear boundaries:

- frontend for tenant workflow
- API for validation and job creation
- database for metadata
- object storage for documents
- queue for work distribution
- workers for expensive processing
- LangGraph for extraction orchestration
- observability for reliability

That design supports larger batches, more companies, safer tenant isolation, and more reliable claim processing.
