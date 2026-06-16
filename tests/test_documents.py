import pytest
from app.api import routes
from app.services.documents import LocalDocuments, object_key
from tests.test_tenant_access import login


def test_authorized_document_and_tamper_detection(client, pdf_bytes):
    headers, owner = login(client)
    job = routes.storage.create_job("private", "fixture.pdf", pdf_bytes, 1, owner["tenant_id"])
    response = client.get(f"/api/claims/{job.job_id}/document", headers=headers)
    assert response.content == pdf_bytes
    assert response.headers["cache-control"] == "no-store"
    other, _ = login(client, "beta")
    assert client.get(f"/api/claims/{job.job_id}/document", headers=other).status_code == 404
    key = object_key(owner["tenant_id"], job.job_id)
    routes.storage.documents.path(key).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="checksum"):
        routes.storage.read_pdf(job.job_id, owner["tenant_id"])


def test_document_paths_are_not_caller_controlled(tmp_path):
    documents = LocalDocuments(tmp_path)
    with pytest.raises(ValueError): documents.get("../../secret")
