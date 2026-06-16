"""Atomic leases and fenced completion for at-least-once task delivery."""
import time
import uuid
from contextlib import contextmanager
from threading import Event, Thread
from sqlalchemy import select, insert, update, func
from app.core.config import settings
from app.db.schema_v1 import jobs, attempts, results
from app.services.storage import utc_now


class AttemptService:
    def __init__(self, store): self.store = store

    def acquire(self, job_id):
        with self.store.db.transaction() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.deleted.is_(False)).with_for_update()).mappings().first()
            if not row or row["status"] != "queued": return None
            number = (connection.execute(select(func.max(attempts.c.number)).where(attempts.c.job_id == job_id)).scalar() or 0)+1
            token = uuid.uuid4().hex
            attempt = dict(id=uuid.uuid4().hex, job_id=job_id, tenant_id=row["tenant_id"], number=number, fence=token, lease_until=time.time()+settings.worker_lease_seconds, status="running", data={"started_at": utc_now()})
            changed = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.version == row["version"], jobs.c.status == "queued").values(status="processing", version=row["version"]+1, data={**row["data"], "status": "processing", "updated_at": utc_now()}))
            if changed.rowcount != 1: return None
            connection.execute(insert(attempts).values(**attempt))
            return attempt

    def _owned(self, connection, fence):
        row = connection.execute(select(attempts).where(attempts.c.fence == fence, attempts.c.status == "running", attempts.c.lease_until > time.time()).with_for_update()).mappings().first()
        if row is None: return None
        job = connection.execute(select(jobs).where(jobs.c.id == row["job_id"], jobs.c.deleted.is_(False), jobs.c.status == "processing").with_for_update()).mappings().first()
        return (row, job) if job else None

    def heartbeat(self, fence):
        with self.store.db.transaction() as connection:
            owned = self._owned(connection, fence)
            if not owned: return False
            connection.execute(update(attempts).where(attempts.c.fence == fence).values(lease_until=time.time()+settings.worker_lease_seconds))
            return True

    def complete(self, fence, response):
        with self.store.db.transaction() as connection:
            owned = self._owned(connection, fence)
            if not owned: return False
            attempt, job = owned
            version = (connection.execute(select(func.max(results.c.version)).where(results.c.job_id == job["id"])).scalar() or 0)+1
            connection.execute(insert(results).values(job_id=job["id"], version=version, tenant_id=job["tenant_id"], data=response.model_dump(mode="json")))
            status = {"success": "succeeded", "succeeded": "succeeded", "partial": "partial"}.get(response.status, "failed")
            connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(status=status, version=job["version"]+1, data={**job["data"], "status": status, "updated_at": utc_now(), "error": None}))
            connection.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(status="completed", data={**attempt["data"], "completed_at": utc_now()}))
            return True

    def fail(self, fence, error="Processing failed."):
        with self.store.db.transaction() as connection:
            owned = self._owned(connection, fence)
            if not owned: return False
            attempt, job = owned
            connection.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(status="failed"))
            connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(status="failed", version=job["version"]+1, data={**job["data"], "status": "failed", "error": error, "updated_at": utc_now()}))
            return True

    @contextmanager
    def keep_alive(self, fence):
        stopped = Event()
        def pulse():
            while not stopped.wait(max(1, settings.worker_lease_seconds/3)):
                try:
                    if not self.heartbeat(fence): break
                except Exception: break
        thread = Thread(target=pulse, daemon=True)
        thread.start()
        try: yield
        finally:
            stopped.set()
            thread.join(timeout=5)
