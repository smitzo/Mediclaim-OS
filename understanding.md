# Document Processor Architecture Understanding

This `understanding.md` was written roughly by Smit, then explained in detail using AI.

## 1. What This Project Does

This project is a medical claim document processor.

In simple words, a user uploads one or many PDF claim documents. Each PDF may contain many pages. Those pages can include claim forms, identity documents, hospital bills, discharge summaries, prescriptions, receipts, reports, and other supporting documents.

The backend reads the PDF, understands what each page is, sends the right pages to the right extraction logic, and produces a structured JSON result.

The frontend gives an operator a dashboard where they can upload many PDFs, see jobs moving through the queue, and inspect the final extracted data.

## 2. Why The Project Was Changed

The earlier version worked like a simple request-response API.

That means:

1. The user uploaded one PDF.
2. The API kept the HTTP request open.
3. The backend processed the whole PDF immediately.
4. The API returned the final answer.

That is acceptable for a small demo or a few pages.

It becomes risky for hundreds of invoices because:

1. A request can stay open for too long.
2. API workers get blocked while doing heavy processing.
3. Large PDFs can use too much memory if every page is rendered into an image.
4. If the server restarts, the in-progress request is lost.
5. Users cannot easily track multiple PDFs.
6. Scaling requires more than just adding one bigger server.

The new architecture treats processing as background jobs.

That means:

1. The user uploads PDFs.
2. The API stores them safely.
3. The API creates job records.
4. The API sends job IDs to a queue.
5. Worker processes pick jobs from the queue.
6. Workers process PDFs independently.
7. Results are saved.
8. The frontend polls job status and shows results when ready.

This is closer to an industry-standard architecture for document processing systems.

## 3. High-Level Flow

The complete flow looks like this:

```text
User
  -> Next.js frontend
  -> FastAPI backend
  -> durable job storage
  -> Redis queue
  -> Celery worker
  -> LangGraph claim pipeline
  -> result storage
  -> frontend result viewer
```

Now let us explain each step slowly.

## 4. Step 1: User Opens The Frontend

The frontend lives inside:

```text
frontend/
```

It is a Next.js application.

Next.js is used because it gives a modern React application structure, production builds, routing, TypeScript support, and good deployment options.

The main page is:

```text
frontend/app/page.tsx
```

This page shows:

1. A batch upload panel.
2. Recent job statistics.
3. A table of recent claim jobs.
4. A result inspector.

The frontend does not process PDFs itself. It only sends files to the backend and displays status/results.

That is important because PDF parsing, LLM calls, and medical document extraction belong on the backend, not inside the browser.

## 5. Step 2: User Uploads One Or Many PDFs

The upload panel allows multiple PDF files.

When the user selects files and clicks the queue button, the frontend calls:

```text
POST /api/claims/batch
```

The API client code is in:

```text
frontend/lib/api.ts
```

That file contains typed functions such as:

```text
submitClaims()
listJobs()
getClaimResult()
```

This keeps API calling logic separate from UI rendering logic.

That is a good architecture choice because if the backend URL or API shape changes, we mostly update the API client instead of rewriting the whole UI.

## 6. Step 3: FastAPI Receives The Upload

The backend entry point is:

```text
main.py
```

`main.py` creates the FastAPI app, configures CORS, and includes the API router.

The route code lives in:

```text
app/api/routes.py
```

Important endpoints are:

```text
POST /api/claims
POST /api/claims/batch
GET /api/claims
GET /api/claims/{job_id}
GET /api/claims/{job_id}/result
POST /api/process
```

`POST /api/process` still exists for compatibility with the older synchronous flow.

The recommended production path is the asynchronous job API:

```text
POST /api/claims
POST /api/claims/batch
```

## 7. Step 4: Backend Validates The PDF

Before accepting a file, the backend checks:

1. The file name ends with `.pdf`.
2. The file is not empty.
3. The file size is within the configured maximum.
4. The PDF can be opened by PyMuPDF.
5. The page count is within the configured maximum.

These limits are configured in:

```text
app/core/config.py
```

Important settings include:

```text
MAX_UPLOAD_BYTES
MAX_PDF_PAGES
DATA_DIR
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
TASK_TIME_LIMIT_SECONDS
```

Validation matters because a production system must protect itself from accidentally huge uploads, corrupted PDFs, and inputs that would consume too much memory or processing time.

## 8. Step 5: Backend Creates A Job

Once the PDF is valid, the backend creates a job record.

The job model is defined in:

```text
app/core/schemas.py
```

The job contains fields like:

```text
job_id
claim_id
filename
status
created_at
updated_at
page_count
file_size_bytes
error
result_url
```

The status can be:

```text
queued
processing
succeeded
partial
failed
```

This is useful because users need visibility. A long-running backend cannot feel like a black box.

## 9. Step 6: Backend Stores The Uploaded PDF

The storage code lives in:

```text
app/services/storage.py
```

Right now it uses file-backed storage.

That means PDFs, job metadata, and results are stored in folders under:

```text
data/
```

The structure is:

```text
data/
  uploads/
  jobs/
  results/
```

This was chosen because it is simple, easy to understand, and works locally without requiring a database.

In a larger production setup, this same storage boundary can later be replaced with:

1. S3 or GCS for uploaded PDFs.
2. PostgreSQL for job metadata.
3. PostgreSQL or object storage for final JSON results.

The important architecture point is that the rest of the app talks to `ClaimStorage`, not directly to random files everywhere.

That makes future migration easier.

## 10. Step 7: Backend Sends The Job To The Queue

After storing the file and metadata, the backend calls Celery:

```text
process_claim_job.delay(job.job_id)
```

The Celery app is defined in:

```text
app/workers/celery_app.py
```

The actual task is in:

```text
app/workers/tasks.py
```

Celery is used because document processing is slow compared with normal API responses.

The API should be fast at accepting uploads and returning job IDs.

The worker should do the heavy processing.

This separation lets us scale in two directions:

1. Add more API containers if many users upload at once.
2. Add more worker containers if many PDFs need processing.

## 11. Step 8: Redis Holds The Queue

Redis is used as the Celery broker and result backend.

In Docker Compose, Redis is defined in:

```text
docker-compose.yml
```

The API and worker both point to Redis.

The API pushes jobs into Redis.

The worker pulls jobs from Redis.

Redis is fast and common for queue workloads.

For a startup MVP, Redis plus Celery is a practical and industry-recognized choice.

## 12. Step 9: Worker Starts Processing

The worker task starts by updating the job status:

```text
processing
```

Then it reads the uploaded PDF bytes from storage.

Then it calls:

```text
process_claim_pdf()
```

That function lives in:

```text
app/services/processor.py
```

This service boundary is important.

The API route and worker task should not both duplicate pipeline logic.

Instead, they both call the same processing service.

That keeps behavior consistent.

## 13. Step 10: LangGraph Runs The Claim Pipeline

The pipeline graph is defined in:

```text
app/core/graph.py
```

The graph shape is:

```text
Segregator
  -> ID Agent
  -> Discharge Agent
  -> Bill Agent
  -> Aggregator
```

In concept:

1. The segregator decides what each page is.
2. The specialist agents extract data from only their assigned pages.
3. The aggregator combines all outputs into one response.

LangGraph is used because the pipeline is agent-like and stateful.

Each node reads and writes shared claim state.

That shared state is represented by:

```text
ClaimState
```

which is defined in:

```text
app/core/schemas.py
```

## 14. Step 11: Segregator Classifies Pages

The segregator code is:

```text
app/agents/segregator.py
```

Its job is to classify every page into one document type.

Document types include:

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

The segregator first extracts text from each page using:

```text
extract_page_texts()
```

from:

```text
app/utils/pdf_utils.py
```

Then it tries local heuristic classification.

Heuristics are simple keyword-based rules.

For example, if a page contains words like invoice, bill number, subtotal, and total amount, it is probably an itemized bill.

This is faster and cheaper than calling an LLM for every page.

## 15. Why Text-First Classification Matters

Many invoices are text-based PDFs.

If a PDF page already has extractable text, rendering it into an image is often unnecessary.

Rendering every page into an image is expensive because:

1. Images use much more memory than text.
2. Base64 image strings are large.
3. Vision model calls are slower.
4. Vision model calls can cost more.

The optimized backend now renders page images lazily.

That means:

1. Extract text first.
2. Use heuristics where possible.
3. Use text-only LLM calls when page text is enough.
4. Render images only for ambiguous or low-text pages that need vision.

This is one of the biggest improvements for hundreds of invoice pages.

## 16. Step 12: Page Routing

After classification, the pipeline builds a map like:

```text
document_type -> list of page numbers
```

For example:

```text
itemized_bill -> [3, 4, 5, 6]
identity_document -> [0, 1]
discharge_summary -> [2]
```

The mapping from document type to agent is defined in:

```text
AGENT_DOCUMENT_MAP
```

inside:

```text
app/core/schemas.py
```

This is important because specialist agents should not process the whole PDF.

The bill agent should process bill pages.

The ID agent should process identity, claim form, and bank pages.

The discharge agent should process discharge summary and prescription pages.

This saves time, reduces cost, and improves accuracy.

## 17. Step 13: ID Agent Extracts Identity Data

The ID agent lives in:

```text
app/agents/id_agent.py
```

It extracts fields like:

```text
patient_name
date_of_birth
gender
address
contact_number
policy_number
insurance_provider
bank_account_number
bank_name
ifsc_routing_number
swift_code
```

It first tries deterministic text extraction from:

```text
app/utils/text_extractors.py
```

If deterministic extraction finds enough signal, it returns without calling the LLM.

If not, it uses the LLM.

If text is enough, it uses a text-only LLM call.

If text is not enough, it renders only the needed pages and uses a vision call.

## 18. Step 14: Discharge Agent Extracts Clinical Data

The discharge agent lives in:

```text
app/agents/discharge_agent.py
```

It extracts fields like:

```text
admission_date
discharge_date
length_of_stay
final_diagnosis
attending_physician
hospital_name
treatment_summary
discharge_medications
prescriptions
follow_up_instructions
```

It uses the same text-first strategy:

1. Try deterministic extraction.
2. Use text-only LLM if possible.
3. Use vision only when needed.

## 19. Step 15: Bill Agent Extracts Billing Data

The bill agent lives in:

```text
app/agents/bill_agent.py
```

It extracts fields like:

```text
bill_number
bill_date
hospital_name
patient_name
line_items
subtotal
tax
discount
insurance_payment
total_amount
patient_responsibility
payment_method
```

Billing can be the biggest part of a claim.

A claim may contain many pages of itemized bills.

That is why billing extraction is chunked.

The code processes billing pages in smaller groups instead of sending everything at once.

This prevents a single huge model call and makes failures easier to isolate.

## 20. Step 16: Aggregator Builds Final Response

The aggregator lives in:

```text
app/agents/aggregator.py
```

It combines:

1. Page classification results.
2. Identity extraction.
3. Discharge extraction.
4. Bill extraction.
5. Errors.
6. Processing summary.

It returns:

```text
ClaimResponse
```

The response contains:

```text
claim_id
status
page_classification
extracted_data
errors
processing_summary
```

The status can be:

```text
success
partial
failed
```

The job status later maps this into:

```text
succeeded
partial
failed
```

## 21. Step 17: Worker Saves The Result

After processing finishes, the worker writes the final JSON response into:

```text
data/results/
```

Then it updates the job metadata.

If processing succeeded:

```text
status = succeeded
```

If some errors happened but partial data exists:

```text
status = partial
```

If processing failed completely:

```text
status = failed
```

This makes results durable.

The frontend can fetch the result later even if the first browser tab was closed.

## 22. Step 18: Frontend Polls Jobs

The frontend periodically calls:

```text
GET /api/claims
```

This returns recent jobs.

If any job is `queued` or `processing`, the frontend refreshes every few seconds.

Polling is simple and reliable for this kind of dashboard.

Later, this can be upgraded to WebSockets or Server-Sent Events if real-time updates become important.

For a startup MVP, polling is easier to operate.

## 23. Step 19: User Inspects Result

When a job is finished or partial, the user clicks Inspect.

The frontend calls:

```text
GET /api/claims/{job_id}/result
```

The backend reads the result JSON from storage and returns it.

The frontend shows it in the result inspector.

This helps operators quickly verify extracted data.

## 24. Why FastAPI

FastAPI is used because:

1. It is fast.
2. It has strong support for async endpoints.
3. It integrates well with Pydantic models.
4. It automatically creates Swagger docs.
5. It is widely used for Python APIs.

For this project, FastAPI is a good fit because the backend is Python-heavy due to PDF parsing, LangGraph, and LLM processing.

## 25. Why Pydantic

Pydantic is used for schemas.

Schemas define the shape of data.

For example:

```text
ClaimJob
ClaimState
ClaimResponse
IdentityData
ItemizedBillData
DischargeSummaryData
```

Pydantic helps by:

1. Validating data.
2. Giving typed Python objects.
3. Producing clean JSON responses.
4. Making API contracts easier to understand.

## 26. Why Celery

Celery is used for background jobs.

Document processing can take seconds or minutes.

An HTTP request should not stay open that long.

Celery lets the API hand work to workers.

This makes the backend more scalable and more reliable.

## 27. Why Redis

Redis is used as the queue.

The API places job messages into Redis.

The worker reads job messages from Redis.

Redis is fast, popular, and simple to run locally with Docker.

## 28. Why Docker Compose

The file:

```text
docker-compose.yml
```

starts:

1. Redis.
2. FastAPI API server.
3. Celery worker.
4. Shared data volume.

This is useful because the real system is not one process anymore.

It is multiple services working together.

Docker Compose makes that easy to run during development and demos.

## 29. Why Next.js

Next.js is used for the frontend because:

1. It is a production-grade React framework.
2. It supports TypeScript well.
3. It gives good build tooling.
4. It has a clean app directory structure.
5. It can be deployed separately from the backend.

The frontend is intentionally not a marketing landing page.

It is an operational dashboard.

Users of this product need to upload, monitor, inspect, and repeat.

## 30. Why Tailwind CSS

Tailwind CSS is used for styling.

The project avoids raw custom CSS for the dashboard.

Tailwind keeps styling close to the component markup and makes it fast to build consistent UI.

For a small team, this reduces context switching between component files and separate CSS files.

## 31. Why The UI Is Dense And Operational

This product is for claim document processing.

That means the UI should feel like a work tool.

The frontend uses:

1. Job tables.
2. Status pills.
3. Metrics.
4. Upload controls.
5. JSON result inspection.

It avoids a decorative landing-page style because operators need clarity and speed.

## 32. Important Scalability Choices

The major scalability choices are:

1. Async job submission instead of blocking HTTP requests.
2. Celery workers for distributed processing.
3. Redis queue for decoupling API and workers.
4. Durable job metadata and result storage.
5. Text-first extraction.
6. Lazy PDF page image rendering.
7. Page routing to specialist agents.
8. Chunked billing extraction.
9. Batch upload endpoints.
10. Frontend polling for long-running jobs.

Together, these make the project more capable of handling hundreds of invoices.

## 33. What Happens If There Are Hundreds Of Invoices

If the user uploads hundreds of PDFs:

1. The frontend sends them to the batch endpoint.
2. The backend validates each file.
3. Each accepted file becomes a separate job.
4. Jobs are pushed into Redis.
5. Workers pull jobs one by one.
6. More workers can be added to process jobs faster.
7. The frontend keeps showing statuses.

This is much better than one giant synchronous request.

## 34. What Happens If One Job Fails

If one PDF fails:

1. The worker marks only that job as failed.
2. Other jobs continue processing.
3. The frontend shows the failed status.
4. The job error is stored in metadata.

This isolation is important.

One bad invoice should not break the entire batch.

## 35. What Happens If A Worker Crashes

Celery is configured with late acknowledgements.

That means a task is acknowledged after work is handled, not before.

This helps avoid losing jobs if a worker dies during processing.

In a full production environment, this should be paired with strong broker settings, monitoring, retries, and idempotent storage writes.

## 36. What Could Be Improved Next

Good next steps are:

1. Replace file-backed job storage with PostgreSQL.
2. Replace local uploaded PDF storage with S3 or GCS.
3. Add authentication and role-based access.
4. Add tenant/company separation.
5. Add automated tests for API routes and storage.
6. Add job retry controls.
7. Add observability with structured logs, metrics, and traces.
8. Add data review/edit screens instead of only JSON.
9. Add export to CSV, Excel, or claim management systems.
10. Add WebSocket/SSE job updates if polling becomes too slow.

## 37. Mental Model For Beginners

Think of the system like a hospital document office.

The frontend is the reception desk.

The FastAPI backend is the clerk who accepts documents and gives a tracking number.

Redis is the tray where pending work is placed.

Celery workers are the staff members who pick files from the tray.

LangGraph is the internal checklist for reading a file.

The segregator is the person who sorts pages into piles.

The ID agent reads ID and policy papers.

The discharge agent reads medical summary papers.

The bill agent reads invoices and receipts.

The aggregator combines everyone’s notes into one final report.

The storage folder is the filing cabinet.

The frontend result viewer is where the user reads the final report.

That is the whole system from beginning to end.

