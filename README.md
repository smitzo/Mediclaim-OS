# Claim Processing Pipeline

FastAPI + LangGraph service for medical claim PDF processing.

This project accepts PDF claim documents, stores them as durable jobs, classifies each page into a document type, routes only the relevant pages to specialist extraction agents, and stores one aggregated JSON result per claim.

Video explanation: https://drive.google.com/file/d/1AT5ryQddgM56CS5ozJYVw5A70nFkQiWl/view

## Workflow

The LangGraph workflow follows this structure:

`START -> Segregator -> [ID Agent, Discharge Summary Agent, Itemized Bill Agent] -> Aggregator -> END`

### Node Responsibilities

- `Segregator`
  Classifies PDF pages into the required document types:
  `claim_forms`, `cheque_or_bank_details`, `identity_document`, `itemized_bill`, `discharge_summary`, `prescription`, `investigation_report`, `cash_receipt`, `other`

- `ID Agent`
  Processes only pages related to identity, claim forms, and bank details.
  Extracts patient, policy, and bank-related fields.

- `Discharge Summary Agent`
  Processes only discharge summary and prescription pages.
  Extracts diagnosis, admission/discharge dates, physician, and medication details.

- `Itemized Bill Agent`
  Processes only bill, receipt, and investigation pages.
  Extracts billing line items and totals.

- `Aggregator`
  Merges all outputs into one final API response.

## How It Works

### 1. API Input

The service exposes the production async API:

- `POST /api/claims`
- `POST /api/claims/batch`
- `GET /api/claims`
- `GET /api/claims/{job_id}`
- `GET /api/claims/{job_id}/result`

It also keeps the original compatibility endpoint:

- `POST /api/process`

Inputs:

- `claim_id`: string
- `file`: PDF upload

Async output:

- job metadata with a `job_id`
- status transitions: `queued`, `processing`, `succeeded`, `partial`, `failed`
- result JSON once processing is complete

Synchronous output:

- JSON with page classifications, extracted structured data, errors, and a processing summary.

### 2. Segregation

The segregator first extracts page text from the PDF and renders page images.

To improve reliability and memory use, segregation uses a hybrid strategy:

- local text heuristics first for obvious pages
- the configured LLM only for pages that are still ambiguous
- fallback page-level classification if a chunk fails
- lazy page rendering so hundreds of text-based invoice pages are not all converted to images

This reduces API usage and keeps the workflow stable for larger PDFs.

### 3. Page Routing

After classification, only relevant pages are sent to each extraction agent:

- `ID Agent` gets `claim_forms`, `cheque_or_bank_details`, `identity_document`
- `Discharge Agent` gets `discharge_summary`, `prescription`
- `Bill Agent` gets `itemized_bill`, `cash_receipt`, `investigation_report`

This follows the assignment rule that extraction agents should not process the whole PDF.

### 4. Extraction

Each extraction agent now uses a text-first strategy:

- deterministic text extraction is attempted first
- OpenAI or the configured LLM is used only if needed

This makes the pipeline more stable when model JSON output is incomplete or rate-limited.

### 5. Aggregation

The aggregator combines:

- page classifications
- extracted identity data
- extracted discharge summary data
- extracted bill data
- processing summary
- error list

Then it returns one final `ClaimResponse`.

## Project Structure

```text
app/
  agents/
    segregator.py
    id_agent.py
    discharge_agent.py
    bill_agent.py
    aggregator.py
  api/
    routes.py
  core/
    graph.py
    schemas.py
    config.py
  utils/
    llm_client.py
    pdf_utils.py
    text_extractors.py
main.py
requirements.txt
```

## Tech Stack

- FastAPI
- LangGraph
- Pydantic
- PyMuPDF
- OpenAI API by default, optional Gemini fallback

## Local Installation

The project has two runtimes:

- backend: FastAPI, Celery, LangGraph, PyMuPDF
- frontend: Next.js dashboard

The backend should be installed inside a Python virtual environment. The frontend uses `npm` from the `frontend/` directory.

### 1. Create and activate a Python virtual environment

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Upgrade packaging tools:

```bash
python -m pip install --upgrade pip setuptools wheel
```

### 2. Install backend dependencies

With the virtual environment activated:

```bash
pip install --require-hashes -r requirements.lock
```

Quick sanity check:

```bash
python -m compileall app
```

For development and regression tests, install `requirements-dev.lock` with
`pip install --require-hashes -r requirements-dev.lock`, then run `pytest -q`.
The locks include transitive dependencies and distribution hashes. Regenerate
them from the input files with `uv pip compile --python-version 3.11
--generate-hashes requirements.txt -o requirements.lock` (and the corresponding
development input/output).

### 3. Configure backend environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
GOOGLE_API_KEY=your_google_gemini_api_key_optional
GEMINI_MODEL=gemini-3-flash-preview
APP_ENV=development
LOG_LEVEL=INFO
DATA_DIR=data
MAX_UPLOAD_BYTES=209715200
MAX_PDF_PAGES=500
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
WORKER_CONCURRENCY=2
TASK_TIME_LIMIT_SECONDS=3600
```

`OPENAI_API_KEY` is needed for OpenAI-backed extraction. Some local/demo flows still work without it, but full pipeline extraction depends on the configured LLM provider.

To use Gemini instead, set:

```env
LLM_PROVIDER=gemini
GOOGLE_API_KEY=your_google_gemini_api_key
```

### 4. Start Redis locally

Async claim jobs require Redis because Celery uses it as the broker/result backend.

If Docker is available:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
```

Alternatively, run Redis from your OS package manager if you already have it installed.

### 5. Run the backend API

In one terminal, with `.venv` activated:

```bash
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/docs
```

Health and metrics:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/metrics
```

### 6. Run the Celery worker

In a second terminal, with `.venv` activated:

```bash
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --concurrency=2
```

Use this worker when testing:

- `POST /api/claims`
- `POST /api/claims/batch`
- dashboard uploads
- queued background processing

The legacy `POST /api/process` endpoint runs synchronously and does not require Celery.

### 7. Install frontend dependencies

In a third terminal:

```bash
cd frontend
npm install
```

Copy the frontend environment file:

```bash
cp .env.example .env.local
```

The default value points to the local backend:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

### 8. Run the frontend dashboard

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

If port `3000` is busy:

```bash
npm run dev -- --port 3001
```

### 9. Demo login and sample PDFs

Use the built-in demo bypass:

```text
username: demo
password: demo
```

When signed in as the demo user, the upload panel shows sample PDFs generated from `data/sample_data.pdf`. Select one demo PDF and click `Process demo PDF data` to populate demo outputs in the dashboard.

### 10. Verification commands

Run these before committing changes:

```bash
python -m compileall app
python scripts/evaluate_sample_dataset.py
cd frontend
npm run typecheck
```

`scripts/evaluate_sample_dataset.py` checks the committed sample PDF fixtures and does not call external LLM services.

## Docker Compose Setup

You can run the API, worker, Redis, and shared data volume together:

```bash
cp .env.example .env
docker compose up --build
```

This starts:

- FastAPI API server on `http://127.0.0.1:8000`
- Celery worker
- Redis queue and result backend
- shared durable storage volume for uploaded PDFs, jobs, auth sessions, reviews, and results

The frontend is still run separately from `frontend/` unless you add it to Compose.

## Example API Flow

1. User uploads a claim PDF.
2. The segregator classifies every page.
3. Relevant pages are routed to the three extraction agents.
4. Each agent extracts structured information from only its assigned pages.
5. The aggregator combines everything into one JSON response.

## Notes

- Small and text-based PDFs work best because deterministic extraction can recover fields even if LLM JSON is incomplete.
- Large batches should use the async job endpoints so HTTP workers are not blocked.
- Large PDFs may still depend on LLM quota and rate limits, but text-first extraction and lazy rendering reduce unnecessary model calls and memory usage.
- The system logs every stage to make debugging easier.

## Submission Summary

This project satisfies the assignment requirements by:

- exposing `POST /api/process`
- using LangGraph orchestration
- including one AI-powered segregator node
- routing only relevant pages to the extraction agents
- using three required extraction agents
- aggregating all outputs into one final JSON response
