from sqlalchemy import update
from app.db.schema_v1 import memberships
import pytest
from app.api import routes
from tests.test_tenant_access import login
from app.core.schemas import ClaimResponse


def set_role(client, role):
    headers, session = login(client)
    with routes.auth_store.db.transaction() as connection:
        connection.execute(update(memberships).values(role=role))
    session = client.post("/api/auth/sign-in", json={"username": "alpha", "password": "test-password-123"}).json()
    client.headers["X-CSRF-Token"] = session["csrf_token"]
    return {"Cookie": "; ".join(f"{k}={v}" for k, v in client.cookies.items()), "X-CSRF-Token": session["csrf_token"]}, session


@pytest.mark.parametrize("role,upload,review", [("uploader", 202, 403), ("reviewer", 403, 200), ("administrator", 202, 200)])
def test_roles_and_server_attribution(client, pdf_bytes, role, upload, review):
    headers, session = set_role(client, role)
    response = client.post("/api/claims", headers=headers, data={"claim_id": "role-test"}, files={"file": ("fixture.pdf", pdf_bytes)})
    assert response.status_code == upload
    job = routes.storage.create_job("review", "fixture.pdf", pdf_bytes, 1, session["tenant_id"])
    routes.storage.save_result(job.job_id, ClaimResponse(claim_id="review", status="success"))
    response = client.put(f"/api/claims/{job.job_id}/review", headers=headers, json={"status": "needs_review", "reviewer": "forged", "expected_version": 0, "result_version": 1})
    assert response.status_code == review
    if review == 200:
        assert response.json()["reviewer"] == "alpha"
