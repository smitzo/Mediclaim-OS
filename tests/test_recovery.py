from sqlalchemy import update
from app.api import routes
from app.db.schema_v1 import attempts
from app.services.attempts import AttemptService
from app.core.schemas import ClaimResponse
from app.core.config import settings
from tests.test_tenant_access import login


def test_crash_recovery_stale_fence_and_retry_exhaustion(client, pdf_bytes, monkeypatch):
    monkeypatch.setattr(settings, "processing_max_attempts", 2)
    _, owner = login(client)
    job = routes.storage.create_job("recover", "claim.pdf", pdf_bytes, 1, owner["tenant_id"])
    service = AttemptService(routes.storage)
    old = service.acquire(job.job_id)
    with routes.storage.db.transaction() as connection:
        connection.execute(update(attempts).values(lease_until=0))
    assert service.reconcile() == 1
    current = service.acquire(job.job_id)
    assert not service.complete(old["fence"], ClaimResponse(claim_id="stale", status="success"))
    service.fail(current["fence"], retryable=True)
    assert routes.storage.get_job(job.job_id).status == "failed"
    routes.storage.retry_job(job.job_id, owner["tenant_id"])
    new = service.acquire(job.job_id)
    assert service.complete(new["fence"], ClaimResponse(claim_id="recovered", status="success"))
    assert routes.storage.get_result(job.job_id).claim_id == "recovered"
