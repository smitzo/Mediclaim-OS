import json
import pytest
from app.api import routes
from tests.test_tenant_access import login


def set_role(client, role):
    headers, session = login(client)
    path = routes.auth_store.accounts_path
    accounts = json.loads(path.read_text())
    accounts[0]["role"] = role
    path.write_text(json.dumps(accounts))
    session = client.post("/api/auth/sign-in", json={"username": "alpha", "password": "test-password-123"}).json()
    return {"Authorization": f"Bearer {session['token']}"}, session


@pytest.mark.parametrize("role,upload,review", [("uploader", 202, 403), ("reviewer", 403, 200), ("administrator", 202, 200)])
def test_roles_and_server_attribution(client, pdf_bytes, role, upload, review):
    headers, session = set_role(client, role)
    response = client.post("/api/claims", headers=headers, data={"claim_id": "role-test"}, files={"file": ("fixture.pdf", pdf_bytes)})
    assert response.status_code == upload
    job = routes.storage.create_job("review", "fixture.pdf", pdf_bytes, 1, session["tenant_id"])
    response = client.put(f"/api/claims/{job.job_id}/review", headers=headers, json={"status": "approved", "reviewer": "forged"})
    assert response.status_code == review
    if review == 200:
        assert response.json()["reviewer"] == "alpha"
