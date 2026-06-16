from __future__ import annotations
import logging
import hmac
import secrets


from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, Request, Response
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
    AuthMemberRequest,
    JobStatus,
)
from app.services.processor import process_claim_pdf
from app.services.auth import auth_store
from app.services.storage import storage
from app.utils.pdf_utils import get_page_count
from app.workers.tasks import process_claim_job

logger = logging.getLogger(__name__)

SESSION_COOKIE = "claimops_session"
CSRF_COOKIE = "claimops_csrf"


async def _csrf_guard(request: Request) -> None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    origin = request.headers.get("origin")
    allowed = {v.strip() for v in settings.allowed_origins.split(",")}
    if origin and origin not in allowed:
        raise HTTPException(status_code=403, detail="Request origin is not allowed.")
    cookie = request.cookies.get(CSRF_COOKIE, "")
    header = request.headers.get("X-CSRF-Token", "")
    if not cookie or not header or not hmac.compare_digest(cookie, header):
        raise HTTPException(status_code=403, detail="Valid CSRF protection is required.")


router = APIRouter(dependencies=[Depends(_csrf_guard)])


def _session_response(request: Request, response: Response, session: AuthSession) -> AuthSession:
    for key, value in ((SESSION_COOKIE, session.token), (CSRF_COOKIE, session.csrf_token)):
        response.set_cookie(key, value, max_age=settings.auth_token_ttl_seconds,
                            httponly=True, secure=settings.auth_cookie_secure, samesite="lax", path="/")
    response.headers["Cache-Control"] = "no-store"
    return session


@router.get("/auth/csrf", tags=["Auth"])
async def csrf(request: Request, response: Response):
    token = request.cookies.get(CSRF_COOKIE) or secrets.token_urlsafe(32)
    response.set_cookie(CSRF_COOKIE, token, httponly=True, secure=settings.auth_cookie_secure, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return {"csrf_token": token}


@router.post("/auth/register-company", response_model=AuthSession, tags=["Auth"])
async def register_company(payload: AuthRegisterRequest, request: Request, response: Response) -> AuthSession:
    auth_store.limit_auth(request.client.host if request.client else "unknown", payload.username)
    return _session_response(request, response, auth_store.register(payload.company_name, payload.username, payload.password))


@router.post("/auth/sign-in", response_model=AuthSession, tags=["Auth"])
async def sign_in(payload: AuthSigninRequest, request: Request, response: Response) -> AuthSession:
    auth_store.limit_auth(request.client.host if request.client else "unknown", payload.username)
    return _session_response(request, response, auth_store.signin(payload.username, payload.password))


@router.post("/auth/sign-out", tags=["Auth"])
async def sign_out(request: Request, response: Response) -> dict[str, str]:
    token = request.cookies.get(SESSION_COOKIE)
    if token and not auth_store.verify_csrf(token, request.headers.get("X-CSRF-Token", "")):
        raise HTTPException(status_code=403, detail="Invalid session CSRF token.")
    auth_store.signout(token)
    response.delete_cookie(SESSION_COOKIE, secure=settings.auth_cookie_secure, httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, secure=settings.auth_cookie_secure, httponly=True, samesite="lax")
    return {"status": "signed_out"}


async def _current_session(
    request: Request,
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> AuthSession:
    token = request.cookies.get(SESSION_COOKIE)
    session = auth_store.authenticate(token)
    csrf = request.cookies.get(CSRF_COOKIE, "")
    if request.method not in {"GET", "HEAD", "OPTIONS"} and not auth_store.verify_csrf(token, csrf):
        raise HTTPException(status_code=403, detail="Invalid session CSRF token.")
    if tenant_id is not None and tenant_id.strip() != session.tenant_id:
        raise HTTPException(status_code=403, detail="Tenant header conflicts with the authenticated session.")
    return session.model_copy(update={"csrf_token": csrf})


def require_role(*allowed: str):
    async def authorized(session: AuthSession = Depends(_current_session)) -> AuthSession:
        if session.role not in allowed:
            raise HTTPException(status_code=403, detail="Your role does not permit this operation.")
        return session
    return authorized


_upload_session = require_role("uploader", "administrator")
_review_session = require_role("reviewer", "administrator")


@router.post("/auth/users", tags=["Auth"])
async def create_member(payload: AuthMemberRequest, session: AuthSession = Depends(require_role("administrator"))):
    return auth_store.add_member(session, payload.username, payload.password, payload.role)


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
    session: AuthSession = Depends(_upload_session),
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
    session: AuthSession = Depends(_upload_session),
) -> ClaimJobSubmitResponse:
    pdf_bytes, page_count = await _validated_pdf(file)
    job = storage.create_job(claim_id, file.filename or "claim.pdf", pdf_bytes, page_count, session.tenant_id)
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
    session: AuthSession = Depends(_upload_session),
) -> ClaimBatchSubmitResponse:
    jobs: list[ClaimJob] = []
    rejected: list[dict[str, str]] = []

    for index, upload in enumerate(files):
        claim_id = _claim_id_for_upload(upload, index, claim_ids)
        try:
            pdf_bytes, page_count = await _validated_pdf(upload)
            job = storage.create_job(claim_id, upload.filename or f"{claim_id}.pdf", pdf_bytes, page_count, session.tenant_id)
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
    session: AuthSession = Depends(_current_session),
) -> list[ClaimJob]:
    bounded_limit = max(1, min(limit, 500))
    bounded_offset = max(0, offset)
    return storage.list_jobs(
        limit=bounded_limit,
        tenant_id=session.tenant_id,
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
async def get_claim_job(job_id: str, session: AuthSession = Depends(_current_session)) -> ClaimJob:
    job = storage.get_job(job_id)
    _ensure_tenant_access(job, session.tenant_id)
    return job


@router.get("/claims/{job_id}/document", tags=["Claims"])
async def get_claim_document(job_id: str, session: AuthSession = Depends(_current_session)):
    content = storage.read_pdf(job_id, session.tenant_id)
    return Response(content, media_type="application/pdf", headers={"Cache-Control": "no-store", "Content-Disposition": 'inline; filename="claim.pdf"', "X-Content-Type-Options": "nosniff"})


@router.get(
    "/claims/{job_id}/result",
    response_model=ClaimResponse,
    summary="Get a completed claim extraction result",
    tags=["Claims"],
)
async def get_claim_result(job_id: str, session: AuthSession = Depends(_current_session)) -> ClaimResponse:
    return storage.get_result(job_id, session.tenant_id)


@router.get(
    "/claims/{job_id}/review",
    response_model=ClaimReview,
    summary="Get the human review state for a claim",
    tags=["Claims"],
)
async def get_claim_review(job_id: str, session: AuthSession = Depends(_current_session)) -> ClaimReview:
    return storage.get_review(job_id, session.tenant_id)


@router.put(
    "/claims/{job_id}/review",
    response_model=ClaimReview,
    summary="Save the human review state for a claim",
    tags=["Claims"],
)
async def save_claim_review(
    job_id: str,
    payload: ClaimReviewUpdate,
    session: AuthSession = Depends(_review_session),
) -> ClaimReview:
    return storage.save_review(job_id, session.tenant_id, payload.model_copy(update={"reviewer": session.username}))


@router.post(
    "/claims/{job_id}/retry",
    response_model=ClaimJob,
    status_code=202,
    summary="Retry a failed or partial claim job",
    tags=["Claims"],
)
async def retry_claim_job(job_id: str, session: AuthSession = Depends(_upload_session)) -> ClaimJob:
    job = storage.retry_job(job_id, session.tenant_id)
    _enqueue_job(job)
    return job


async def _validated_pdf(file: UploadFile) -> tuple[bytes, int]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if len(file.filename) > 180:
        raise HTTPException(status_code=400, detail="Uploaded filename is too long.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not pdf_bytes.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a PDF.")
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



def _ensure_tenant_access(job: ClaimJob, tenant_id: str) -> None:
    if job.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Claim job not found.")
