import pytest
from app.api import routes
from app.core.schemas import ClaimResponse


def login(client, name="alpha"):
    response = client.post("/api/auth/register-company", json={
        "company_name": name, "username": name, "password": "test-password-123"})
    assert response.status_code == 200
    session = response.json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    return {"Cookie": "; ".join(f"{k}={v}" for k, v in client.cookies.items()), "X-CSRF-Token": session["csrf_token"]}, session


@pytest.mark.parametrize("method,path", [
    ("get", "/api/claims"), ("post", "/api/claims"), ("post", "/api/claims/batch"),
    ("post", "/api/process"), ("get", "/api/claims/unknown"),
    ("get", "/api/claims/unknown/result"), ("get", "/api/claims/unknown/review"),
    ("put", "/api/claims/unknown/review"), ("post", "/api/claims/unknown/retry"),
])
def test_every_claim_operation_requires_auth(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_tenant_header_cannot_switch_principal(client, pdf_bytes):
    headers, owner = login(client)
    job = routes.storage.create_job("synthetic", "claim.pdf", pdf_bytes, 1, owner["tenant_id"])
    routes.storage.save_result(job.job_id, ClaimResponse(claim_id="synthetic", status="success"))
    other_headers, other = login(client, "beta")
    assert client.get("/api/claims", headers=other_headers).json() == []
    for suffix in ("", "/result", "/review"):
        assert client.get(f"/api/claims/{job.job_id}{suffix}", headers=other_headers).status_code == 404
    assert client.get("/api/claims", headers={**headers, "X-Tenant-ID": other["tenant_id"]}).status_code == 403
    assert client.get(f"/api/claims/{job.job_id}", headers=headers).status_code == 200
    assert client.post(f"/api/claims/{job.job_id}/retry", headers=other_headers).status_code == 404
    assert client.put(f"/api/claims/{job.job_id}/review", headers=other_headers, json={"status": "approved", "expected_version": 0, "result_version": 1}).status_code == 404
