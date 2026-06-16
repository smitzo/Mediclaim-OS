import json
import pytest
from app.services.legacy_import import inspect_legacy, apply_import
from app.services.storage import ClaimStorage
from app.api import routes
from tests.test_tenant_access import login
from sqlalchemy import select
from app.db.schema_v1 import users


def test_import_preserves_ids_and_is_repeatable(client, tmp_path, pdf_bytes):
    _, owner = login(client)
    with routes.auth_store.db.engine.connect() as connection:
        account = dict(connection.execute(select(users)).mappings().first())
    account.update(tenant_id=owner["tenant_id"], company_name=owner["company_name"], role="administrator")
    job = routes.storage.create_job("legacy", "claim.pdf", pdf_bytes, 1, owner["tenant_id"])
    source = tmp_path/"legacy"
    for directory in ("auth", "jobs", "uploads"): (source/directory).mkdir(parents=True)
    (source/"auth/auth_accounts.json").write_text(json.dumps([account]))
    (source/f"jobs/{job.job_id}.json").write_text(job.model_dump_json())
    (source/f"uploads/{job.job_id}.pdf").write_bytes(pdf_bytes)
    accounts, claims = inspect_legacy(source)
    target = ClaimStorage(tmp_path/"new")
    assert apply_import(target, accounts, claims)["jobs"] == 1
    assert apply_import(target, accounts, claims)["jobs"] == 0
    assert target.get_job(job.job_id).created_at == job.created_at
    assert target.read_pdf(job.job_id) == pdf_bytes
    job.tenant_id = "default"
    (source/f"jobs/{job.job_id}.json").write_text(job.model_dump_json())
    with pytest.raises(ValueError, match="ownership"): inspect_legacy(source)
