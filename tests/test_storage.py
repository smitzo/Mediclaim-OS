from concurrent.futures import ThreadPoolExecutor
from app.services.storage import ClaimStorage
from app.core.schemas import ClaimResponse


def test_restart_persistence_and_immutable_results(tmp_path, pdf_bytes):
    first = ClaimStorage(tmp_path)
    job = first.create_job("synthetic", "fixture.pdf", pdf_bytes, 1, "tenant-a")
    first.save_result(job.job_id, ClaimResponse(claim_id="old", status="partial"))
    first.save_result(job.job_id, ClaimResponse(claim_id="new", status="success"))
    second = ClaimStorage(tmp_path)
    assert second.get_job(job.job_id).tenant_id == "tenant-a"
    assert second.get_result(job.job_id, "tenant-a").claim_id == "new"
    assert second.read_pdf(job.job_id) == pdf_bytes
    assert len(second.list_jobs(tenant_id="tenant-b")) == 0


def test_concurrent_submissions_survive(tmp_path, pdf_bytes):
    store = ClaimStorage(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: store.create_job(str(i), "fixture.pdf", pdf_bytes, 1, "tenant"), range(12)))
    assert len(store.list_jobs(tenant_id="tenant")) == 12
