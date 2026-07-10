from app.core.config import settings
from tests.test_tenant_access import login


def test_limits_and_quotas_apply_to_both_paths(client, pdf_bytes, monkeypatch):
    login(client)
    monkeypatch.setattr(settings, "max_tenant_active_jobs", 1)
    args = {"data": {"claim_id": "bounded"}, "files": {"file": ("fixture.pdf", pdf_bytes)}}
    assert client.post("/api/claims", **args).status_code == 202
    assert client.post("/api/process", **args).status_code == 429
    monkeypatch.setattr(settings, "max_upload_bytes", 10)
    assert client.post("/api/process", **args).status_code == 413
    monkeypatch.setattr(settings, "max_request_bytes", 20)
    assert client.post("/api/claims", **args).status_code == 413


def test_batch_count_is_bounded(client, pdf_bytes, monkeypatch):
    login(client)
    monkeypatch.setattr(settings, "max_batch_files", 1)
    assert client.post("/api/claims/batch", files=[("files", ("a.pdf", pdf_bytes)), ("files", ("b.pdf", pdf_bytes))]).status_code == 413
