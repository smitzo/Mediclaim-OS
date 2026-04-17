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
- Gemini only for pages that are still ambiguous
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
- Gemini is used only if needed

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
- Google Gemini API

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Add environment variables

Create `.env` file:

```env
GOOGLE_API_KEY=your_api_key_here
APP_ENV=development
LOG_LEVEL=INFO
DATA_DIR=data
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

You can copy `.env.example` as the starting point.

### 3. Run the server only

This supports `/api/process` and status reads, but async jobs require Redis and a worker.

```bash
uvicorn main:app --reload
```

### 4. Run the distributed stack

```bash
docker compose up --build
```

This starts:

- FastAPI API server
- Celery worker
- Redis queue and result backend
- shared durable storage volume for uploaded PDFs and results

### 5. Open Swagger UI

```text
http://127.0.0.1:8000/docs
```

## Example API Flow

1. User uploads a claim PDF.
2. The segregator classifies every page.
3. Relevant pages are routed to the three extraction agents.
4. Each agent extracts structured information from only its assigned pages.
5. The aggregator combines everything into one JSON response.

## Notes

- Small and text-based PDFs work best because deterministic extraction can recover fields even if LLM JSON is incomplete.
- Large batches should use the async job endpoints so HTTP workers are not blocked.
- Large PDFs may still depend on Gemini quota and rate limits, but text-first extraction and lazy rendering reduce unnecessary LLM and memory usage.
- The system logs every stage to make debugging easier.

## Submission Summary

This project satisfies the assignment requirements by:

- exposing `POST /api/process`
- using LangGraph orchestration
- including one AI-powered segregator node
- routing only relevant pages to the extraction agents
- using three required extraction agents
- aggregating all outputs into one final JSON response
