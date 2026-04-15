"""Background tasks run by Celery workers."""

from __future__ import annotations

import logging

from app.services.processor import process_claim_pdf
from app.services.storage import storage
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="claims.process", bind=True, autoretry_for=(), max_retries=0)
def process_claim_job(self, job_id: str) -> dict[str, str]:
    """Process one uploaded claim PDF and persist the final result."""
    job = storage.update_job(job_id, "processing")
    logger.info("Worker started job %s for claim %s", job.job_id, job.claim_id)

    try:
        pdf_bytes = storage.read_pdf(job_id)
        response = process_claim_pdf(job.claim_id, pdf_bytes)
        storage.save_result(job_id, response)
        final_status = "partial" if response.status == "partial" else response.status
        if final_status not in {"succeeded", "partial", "failed"}:
            final_status = "succeeded" if response.status == "success" else "failed"
        storage.update_job(job_id, final_status)
        logger.info("Worker completed job %s with status %s", job_id, final_status)
        return {"job_id": job_id, "status": final_status}
    except Exception as exc:
        logger.exception("Worker failed job %s", job_id)
        storage.update_job(job_id, "failed", error=str(exc))
        raise
