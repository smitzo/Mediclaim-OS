"""Tenant-scoped transactional records; private documents use a separate adapter."""
from __future__ import annotations
import hashlib
import json
import re
import uuid
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from fastapi import HTTPException
from sqlalchemy import select, insert, update, func
from app.core.config import settings
from app.core.schemas import ClaimJob, ClaimResponse, ClaimReview, ClaimReviewUpdate, JobStatus
from app.db.database import Database
from app.services.documents import document_store, object_key
from app.db.schema_v1 import jobs, results, reviews, tenants, outbox, idempotency


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimStorage:
    def __init__(self, base_dir: str | Path, database: Database | None = None):
        self.base_dir = Path(base_dir)
        self.documents = document_store(self.base_dir)
        self.db = database or Database(settings.database_url or f"sqlite:///{self.base_dir}/claims.sqlite3", initialize=settings.app_env != "production")

    def _job(self, connection, job_id: str, tenant_id: str | None = None):
        query = select(jobs).where(jobs.c.id == job_id, jobs.c.deleted.is_(False))
        if tenant_id is not None:
            query = query.where(jobs.c.tenant_id == tenant_id)
        row = connection.execute(query).mappings().first()
        if row is None:
            raise HTTPException(status_code=404, detail="Claim job not found.")
        return row

    def create_job(self, claim_id, filename, pdf_bytes, page_count, tenant_id="default", idempotency_key=None) -> ClaimJob:
        if idempotency_key and not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", idempotency_key):
            raise HTTPException(status_code=400, detail="Invalid idempotency key.")
        fingerprint = hashlib.sha256(json.dumps([claim_id, filename, hashlib.sha256(pdf_bytes).hexdigest()]).encode()).hexdigest()
        job_id = uuid.uuid4().hex
        now = utc_now()
        job = ClaimJob(job_id=job_id, tenant_id=tenant_id, claim_id=claim_id,
            filename=re.sub(r"[^A-Za-z0-9_.-]", "-", filename), status="queued", created_at=now, updated_at=now,
            page_count=page_count, file_size_bytes=len(pdf_bytes), result_url=f"/api/claims/{job_id}/result")
        key = object_key(tenant_id, job_id)
        self.documents.put(key, pdf_bytes)
        try:
            with self.db.transaction() as connection:
                tenant = connection.execute(select(tenants).where(tenants.c.id == tenant_id).with_for_update()).first()
                if idempotency_key:
                    previous = connection.execute(select(idempotency).where(idempotency.c.tenant_id == tenant_id, idempotency.c.key == idempotency_key)).mappings().first()
                    if previous:
                        if previous["fingerprint"] != fingerprint:
                            raise HTTPException(status_code=409, detail="Idempotency key was used for another submission.")
                        existing = self._job(connection, previous["job_id"], tenant_id)
                        self.documents.delete(key)
                        return ClaimJob(**existing["data"])
                if not tenant:
                    connection.execute(insert(tenants).values(id=tenant_id, name=tenant_id))
                connection.execute(insert(jobs).values(id=job_id, tenant_id=tenant_id, claim_id=claim_id, status=job.status,
                    created_at=now, version=1, deleted=False, object_key=key, checksum=hashlib.sha256(pdf_bytes).hexdigest(), data=job.model_dump()))
                connection.execute(insert(outbox).values(id=uuid.uuid4().hex, job_id=job_id, tenant_id=tenant_id, published=False, available_at=time.time(), attempts=0))
                if idempotency_key:
                    connection.execute(insert(idempotency).values(tenant_id=tenant_id, key=idempotency_key, fingerprint=fingerprint, job_id=job_id))
        except Exception:
            self.documents.delete(key)
            raise
        return job

    def dispatch_outbox(self, publish, job_id=None, limit=100):
        sent = 0
        with self.db.transaction() as connection:
            query = select(outbox).join(jobs, jobs.c.id == outbox.c.job_id).where(outbox.c.published.is_(False), outbox.c.available_at <= time.time(), jobs.c.deleted.is_(False))
            if job_id: query = query.where(outbox.c.job_id == job_id)
            rows = connection.execute(query.order_by(outbox.c.available_at).limit(limit).with_for_update(skip_locked=True, of=outbox)).mappings().all()
            for row in rows:
                try:
                    publish(row["job_id"])
                except Exception:
                    connection.execute(update(outbox).where(outbox.c.id == row["id"]).values(attempts=row["attempts"]+1, available_at=time.time()+min(60, 2**min(row["attempts"], 6))))
                else:
                    connection.execute(update(outbox).where(outbox.c.id == row["id"]).values(published=True))
                    sent += 1
        return sent

    def get_job(self, job_id: str, tenant_id: str | None = None) -> ClaimJob:
        with self.db.engine.connect() as connection:
            return ClaimJob(**self._job(connection, job_id, tenant_id)["data"])

    def list_jobs(self, limit=100, tenant_id=None, status=None, query=None, offset=0):
        statement = select(jobs.c.data).where(jobs.c.deleted.is_(False))
        if tenant_id is not None: statement = statement.where(jobs.c.tenant_id == tenant_id)
        if status: statement = statement.where(jobs.c.status == status)
        if query: statement = statement.where(jobs.c.claim_id.ilike(f"%{query}%", escape="\\"))
        with self.db.engine.connect() as connection:
            return [ClaimJob(**row[0]) for row in connection.execute(statement.order_by(jobs.c.created_at.desc()).offset(offset).limit(limit))]

    def update_job(self, job_id, status: JobStatus, error=None):
        with self.db.transaction() as connection:
            row = self._job(connection, job_id)
            job = ClaimJob(**row["data"]).model_copy(update={"status": status, "error": error, "updated_at": utc_now()})
            connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.version == row["version"]).values(status=status, data=job.model_dump(), version=row["version"]+1))
            return job

    def retry_job(self, job_id, tenant_id=None):
        with self.db.transaction() as connection:
            row = self._job(connection, job_id, tenant_id)
            job = ClaimJob(**row["data"])
            if job.status not in {"failed", "partial"}:
                raise HTTPException(status_code=409, detail="Only failed or partial jobs can be retried.")
            job.processing_generation += 1
            job.status, job.error, job.retry_count, job.updated_at = "queued", None, job.retry_count+1, utc_now()
            changed = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.version == row["version"]).values(status="queued", data=job.model_dump(), version=row["version"]+1))
            if changed.rowcount != 1: raise HTTPException(status_code=409, detail="Job changed; reload and retry.")
            connection.execute(insert(outbox).values(id=uuid.uuid4().hex, job_id=job_id, tenant_id=job.tenant_id, published=False, available_at=time.time(), attempts=0))
            return job

    def save_result(self, job_id, response):
        with self.db.transaction() as connection:
            job = self._job(connection, job_id)
            version = connection.execute(select(func.max(results.c.version)).where(results.c.job_id == job_id)).scalar() or 0
            connection.execute(insert(results).values(job_id=job_id, version=version+1, tenant_id=job["tenant_id"], data=response.model_dump(mode="json")))

    def get_result(self, job_id, tenant_id=None):
        with self.db.engine.connect() as connection:
            job = self._job(connection, job_id, tenant_id)
            row = connection.execute(select(results.c.data).where(results.c.job_id == job_id, results.c.tenant_id == job["tenant_id"]).order_by(results.c.version.desc())).first()
            if row is None: raise HTTPException(status_code=404, detail="Claim result is not ready yet.")
            return ClaimResponse(**row[0])

    def get_review(self, job_id, tenant_id=None):
        with self.db.engine.connect() as connection:
            job = self._job(connection, job_id, tenant_id)
            row = connection.execute(select(reviews.c.data).where(reviews.c.job_id == job_id, reviews.c.tenant_id == job["tenant_id"])).first()
            return ClaimReview(**row[0]) if row else ClaimReview(job_id=job_id, tenant_id=job["tenant_id"], updated_at=utc_now())

    def save_review(self, job_id, tenant_id, payload):
        with self.db.transaction() as connection:
            job = self._job(connection, job_id, tenant_id)
            review = ClaimReview(job_id=job_id, tenant_id=job["tenant_id"], updated_at=utc_now(), **payload.model_dump())
            previous = connection.execute(select(reviews.c.version).where(reviews.c.job_id == job_id)).scalar()
            if previous is None:
                connection.execute(insert(reviews).values(job_id=job_id, tenant_id=job["tenant_id"], version=1, data=review.model_dump()))
            else:
                connection.execute(update(reviews).where(reviews.c.job_id == job_id).values(version=previous+1, data=review.model_dump()))
            return review

    def read_pdf(self, job_id, tenant_id=None):
        with self.db.engine.connect() as connection:
            row = self._job(connection, job_id, tenant_id)
            content = self.documents.get(row["object_key"])
            if hashlib.sha256(content).hexdigest() != row["checksum"]:
                raise ValueError("Document checksum verification failed.")
            return content


storage = ClaimStorage(settings.data_dir)


def response_to_jsonable(response: ClaimResponse) -> dict[str, Any]:
    return response.model_dump(mode="json")
