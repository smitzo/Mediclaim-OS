from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import update
from app.db.schema_v1 import attempts
from app.services.attempts import AttemptService
from app.api import routes
from app.core.schemas import ClaimResponse
from tests.test_tenant_access import login


def test_duplicate_delivery_and_expired_worker_cannot_commit(client, pdf_bytes):
    _, owner = login(client)
    job = routes.storage.create_job("lease", "fixture.pdf", pdf_bytes, 1, owner["tenant_id"])
    service = AttemptService(routes.storage)
    with ThreadPoolExecutor(max_workers=3) as pool:
        acquired = list(pool.map(lambda _: service.acquire(job.job_id), range(3)))
    lease = next(item for item in acquired if item)
    assert sum(item is not None for item in acquired) == 1
    assert service.heartbeat(lease["fence"])
    with routes.storage.db.transaction() as connection:
        connection.execute(update(attempts).values(lease_until=0))
    assert not service.complete(lease["fence"], ClaimResponse(claim_id="stale", status="success"))
    assert not service.heartbeat(lease["fence"])
