from app.api import routes
from tests.test_tenant_access import login


def test_repeat_submission_and_conflicting_reuse(client, pdf_bytes):
    login(client)
    args = {"headers": {"Idempotency-Key": "test-key"}, "data": {"claim_id": "same"}, "files": {"file": ("claim.pdf", pdf_bytes)}}
    first = client.post("/api/claims", **args)
    second = client.post("/api/claims", **args)
    assert first.status_code == second.status_code == 202
    assert first.json()["job"]["job_id"] == second.json()["job"]["job_id"]
    args["data"] = {"claim_id": "different"}
    assert client.post("/api/claims", **args).status_code == 409
    assert len(routes.storage.list_jobs()) == 1
    login(client, "beta")
    assert client.post("/api/claims", **args).status_code == 202
    assert len(routes.storage.list_jobs()) == 2
