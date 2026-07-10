from sqlalchemy import select
from app.api import routes
from app.db.schema_v1 import audits
from app.core.schemas import ClaimResponse
from tests.test_tenant_access import login


def test_optimistic_review_and_append_only_history(client, pdf_bytes):
    _, owner = login(client)
    job = routes.storage.create_job("review", "claim.pdf", pdf_bytes, 1, owner["tenant_id"])
    routes.storage.save_result(job.job_id, ClaimResponse(claim_id="review", status="success"))
    path = f"/api/claims/{job.job_id}/review"
    payload = {"status": "needs_review", "expected_version": 0, "result_version": 1, "corrected_data": {"identity": {"patient_name": "Corrected Synthetic Patient"}}}
    assert client.put(path, json=payload).status_code == 200
    assert client.put(path, json=payload).status_code == 409
    payload.update(expected_version=1, status="approved")
    assert client.put(path, json=payload).status_code == 422
    assert routes.storage.get_result(job.job_id).extracted_data == {}
    with routes.storage.db.engine.connect() as connection:
        assert len(connection.execute(select(audits)).all()) == 1
