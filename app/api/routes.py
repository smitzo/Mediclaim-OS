from __future__ import annotations
import logging


from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.schemas import (
    ClaimBatchSubmitResponse,
    ClaimJob,
    ClaimJobSubmitResponse,
    ClaimResponse,
    ClaimReview,
    ClaimReviewUpdate,
    AuthRegisterRequest,
    AuthSession,
    AuthSigninRequest,
    JobStatus,
)
from app.services.processor import process_claim_pdf
from app.services.auth import auth_store
from app.services.storage import storage
from app.utils.pdf_utils import get_page_count
from app.workers.tasks import process_claim_job

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/auth/register-company", response_model=AuthSession, tags=["Auth"])
async def register_company(payload: AuthRegisterRequest) -> AuthSession:
    return auth_store.register(payload.company_name, payload.username, payload.password)


@router.post("/auth/sign-in", response_model=AuthSession, tags=["Auth"])
async def sign_in(payload: AuthSigninRequest) -> AuthSession:
    return auth_store.signin(payload.username, payload.password)


@router.post("/auth/sign-out", tags=["Auth"])
async def sign_out(authorization: str | None = Header(default=None)) -> dict[str, str]:
    auth_store.signout(_bearer_token(authorization))
    return {"status": "signed_out"}


def _bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        return None
    return token


def _current_session(authorization: str | None = Header(default=None)) -> AuthSession:
    return auth_store.authenticate(_bearer_token(authorization))


@router.get("/me", response_model=AuthSession, tags=["Auth"])
async def me(session: AuthSession = Depends(_current_session)) -> AuthSession:
    return session


@router.post(
    "/process",
    response_model=ClaimResponse,
    summary="Process a medical insurance claim PDF",
    tags=["Claims"],
)
async def process_claim(
    claim_id: str = Form(..., description="Unique claim identifier"),
    file: UploadFile = File(..., description="Multi-page PDF claim document"),
) -> JSONResponse:
    """
    Upload a multi-page PDF insurance claim and receive structured extracted data.

    The pipeline:
    1. Segregator classifies every page into one of 9 document types.
    2. Three specialist agents extract data in parallel from their assigned pages.
    3. Aggregator combines all results into a single JSON response.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    logger.info("Received claim %s | file=%s | size=%d bytes", claim_id, file.filename, len(pdf_bytes))

    try:
        response = process_claim_pdf(claim_id, pdf_bytes)
    except Exception as exc:
        logger.exception("Pipeline failed for claim %s: %s", claim_id, exc)
        raise HTTPException(status_code=500, detail=f"Processing pipeline error: {exc}")

    logger.info(
        "Pipeline completed for claim %s | status=%s | extracted_sections=%s | errors=%d",
        claim_id,
        response.status,
        sorted(response.extracted_data.keys()),
        len(response.errors),
    )

    return JSONResponse(content=response.model_dump())


@router.post(
    "/claims",
    response_model=ClaimJobSubmitResponse,
    status_code=202,
    summary="Submit one claim PDF for background processing",
    tags=["Claims"],
)
async def submit_claim_job(
    claim_id: str = Form(..., description="Business claim identifier"),
    file: UploadFile = File(..., description="PDF claim document"),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> ClaimJobSubmitResponse:
    pdf_bytes, page_count = await _validated_pdf(file)
    job = storage.create_job(claim_id, file.filename or "claim.pdf", pdf_bytes, page_count, _tenant_id(tenant_id))
    _enqueue_job(job)
    return ClaimJobSubmitResponse(job=job)


@router.post(
    "/claims/batch",
    response_model=ClaimBatchSubmitResponse,
    status_code=202,
    summary="Submit many claim PDFs for background processing",
    tags=["Claims"],
)
async def submit_claim_batch(
    files: list[UploadFile] = File(..., description="One or more PDF claim documents"),
    claim_ids: list[str] | None = Form(None, description="Optional claim IDs matching upload order"),
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> ClaimBatchSubmitResponse:
    jobs: list[ClaimJob] = []
    rejected: list[dict[str, str]] = []

    for index, upload in enumerate(files):
        claim_id = _claim_id_for_upload(upload, index, claim_ids)
        try:
            pdf_bytes, page_count = await _validated_pdf(upload)
            job = storage.create_job(claim_id, upload.filename or f"{claim_id}.pdf", pdf_bytes, page_count, _tenant_id(tenant_id))
            _enqueue_job(job)
            jobs.append(job)
        except HTTPException as exc:
            rejected.append({
                "filename": upload.filename or f"file-{index}",
                "reason": str(exc.detail),
            })
        except Exception as exc:
            logger.exception("Batch submit failed for %s", upload.filename)
            rejected.append({
                "filename": upload.filename or f"file-{index}",
                "reason": str(exc),
            })

    if not jobs and rejected:
        logger.warning("Batch rejected all %d upload(s)", len(rejected))
    return ClaimBatchSubmitResponse(jobs=jobs, rejected=rejected)


@router.get(
    "/claims",
    response_model=list[ClaimJob],
    summary="List recent claim jobs",
    tags=["Claims"],
)
async def list_claim_jobs(
    limit: int = 100,
    offset: int = 0,
    status: JobStatus | None = None,
    q: str | None = None,
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> list[ClaimJob]:
    bounded_limit = max(1, min(limit, 500))
    bounded_offset = max(0, offset)
    return storage.list_jobs(
        limit=bounded_limit,
        tenant_id=_tenant_id(tenant_id),
        status=status,
        query=q,
        offset=bounded_offset,
    )


@router.get(
    "/claims/{job_id}",
    response_model=ClaimJob,
    summary="Get claim job status",
    tags=["Claims"],
)
async def get_claim_job(job_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> ClaimJob:
    job = storage.get_job(job_id)
    _ensure_tenant_access(job, tenant_id)
    return job


@router.get(
    "/claims/{job_id}/result",
    response_model=ClaimResponse,
    summary="Get a completed claim extraction result",
    tags=["Claims"],
)
async def get_claim_result(job_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> ClaimResponse:
    return storage.get_result(job_id, _tenant_id(tenant_id))


@router.get(
    "/claims/{job_id}/review",
    response_model=ClaimReview,
    summary="Get the human review state for a claim",
    tags=["Claims"],
)
async def get_claim_review(job_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> ClaimReview:
    return storage.get_review(job_id, _tenant_id(tenant_id))


@router.put(
    "/claims/{job_id}/review",
    response_model=ClaimReview,
    summary="Save the human review state for a claim",
    tags=["Claims"],
)
async def save_claim_review(
    job_id: str,
    payload: ClaimReviewUpdate,
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> ClaimReview:
    return storage.save_review(job_id, _tenant_id(tenant_id), payload)


@router.post(
    "/claims/{job_id}/retry",
    response_model=ClaimJob,
    status_code=202,
    summary="Retry a failed or partial claim job",
    tags=["Claims"],
)
async def retry_claim_job(job_id: str, tenant_id: str | None = Header(default=None, alias="X-Tenant-ID")) -> ClaimJob:
    job = storage.retry_job(job_id, _tenant_id(tenant_id))
    _enqueue_job(job)
    return job


async def _validated_pdf(file: UploadFile) -> tuple[bytes, int]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(pdf_bytes) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Uploaded PDF exceeds the configured size limit.")

    try:
        page_count = get_page_count(pdf_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Uploaded file is not a valid PDF: {exc}") from exc

    if page_count > settings.max_pdf_pages:
        raise HTTPException(
            status_code=413,
            detail=f"PDF has {page_count} pages; maximum allowed is {settings.max_pdf_pages}.",
        )
    return pdf_bytes, page_count


def _enqueue_job(job: ClaimJob) -> None:
    try:
        process_claim_job.delay(job.job_id)
    except Exception as exc:
        storage.update_job(job.job_id, "failed", error=f"Queue submission failed: {exc}")
        logger.exception("Failed to enqueue job %s", job.job_id)
        raise HTTPException(status_code=503, detail="Processing queue is unavailable.") from exc


def _claim_id_for_upload(upload: UploadFile, index: int, claim_ids: list[str] | None) -> str:
    if claim_ids and index < len(claim_ids) and claim_ids[index].strip():
        return claim_ids[index].strip()
    stem = (upload.filename or f"claim-{index + 1}").rsplit(".", 1)[0]
    return stem or f"claim-{index + 1}"


def _tenant_id(value: str | None) -> str:
    return value.strip() if value and value.strip() else "default"


def _ensure_tenant_access(job: ClaimJob, tenant_id: str | None) -> None:
    if job.tenant_id != _tenant_id(tenant_id):
        raise HTTPException(status_code=404, detail="Claim job not found.")
