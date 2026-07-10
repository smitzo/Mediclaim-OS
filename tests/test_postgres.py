"""Executed against a dedicated PostgreSQL test DB when explicitly configured."""
import os
import uuid
import pytest
from app.db.database import Database
from app.services.storage import ClaimStorage


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="Dedicated PostgreSQL service is not configured")
def test_postgres_repository_roundtrip(tmp_path, pdf_bytes):
    db = Database(os.environ["TEST_POSTGRES_URL"], initialize=False)
    db.check()
    store = ClaimStorage(tmp_path, db)
    tenant = "ci-"+uuid.uuid4().hex
    job = store.create_job("synthetic-postgres", "fixture.pdf", pdf_bytes, 1, tenant)
    assert store.get_job(job.job_id, tenant).claim_id == "synthetic-postgres"
    assert store.read_pdf(job.job_id) == pdf_bytes
