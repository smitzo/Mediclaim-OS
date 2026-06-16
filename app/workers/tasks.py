"""Background execution with atomic leases and fenced result writes."""
import logging
from app.services.processor import process_claim_pdf
from app.services.storage import storage
from app.services.attempts import AttemptService
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="claims.process", bind=True, autoretry_for=(), max_retries=0)
def process_claim_job(self, job_id: str):
    service = AttemptService(storage)
    attempt = service.acquire(job_id)
    if not attempt: return {"job_id": job_id, "status": "ignored"}
    try:
        with service.keep_alive(attempt["fence"]):
            job = storage.get_job(job_id, attempt["tenant_id"])
            response = process_claim_pdf(job.claim_id, storage.read_pdf(job_id, attempt["tenant_id"]))
            committed = service.complete(attempt["fence"], response)
        return {"job_id": job_id, "status": "completed" if committed else "stale"}
    except Exception:
        service.fail(attempt["fence"])
        logger.error("Claim attempt failed", extra={"job_id": job_id})
        return {"job_id": job_id, "status": "failed"}
