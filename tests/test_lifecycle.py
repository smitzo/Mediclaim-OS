from app.api import routes
from app.services.attempts import AttemptService
from app.services.lifecycle import create_backup, restore_backup, delete_claim, deletion_ledger
from app.core.schemas import ClaimResponse
from tests.test_tenant_access import login


def test_deletion_fences_worker_and_restore_respects_latest_ledger(client, tmp_path, pdf_bytes):
    _, owner = login(client)
    job = routes.storage.create_job("private", "fixture.pdf", pdf_bytes, 1, owner["tenant_id"])
    service = AttemptService(routes.storage)
    attempt = service.acquire(job.job_id)
    backup = tmp_path/"backup"
    assert create_backup(routes.storage, backup)["objects"] == 1
    delete_claim(routes.storage, job.job_id, owner["tenant_id"], "alpha")
    assert not service.complete(attempt["fence"], ClaimResponse(claim_id="stale", status="success"))
    assert client.get(f"/api/claims/{job.job_id}").status_code == 404
    restored = restore_backup(backup, tmp_path/"restored", deletion_ledger(routes.storage))
    assert restored.list_jobs() == []
    assert not list((tmp_path/"restored/documents").rglob("*.pdf"))
