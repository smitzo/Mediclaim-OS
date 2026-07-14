"""Atomic leases and fenced completion for at-least-once task delivery."""
import time
import uuid
import random
from datetime import datetime
from contextlib import contextmanager
from threading import Event, Thread
from sqlalchemy import select, insert, update, func
from app.core.config import settings
from app.db.schema_v1 import jobs, attempts, results, outbox
from app.services.storage import utc_now
from app.core.versions import PIPELINE_VERSION, SCHEMA_VERSION, PROMPT_VERSION


class AttemptService:
    def __init__(self, store): self.store = store

    def acquire(self, job_id):
        with self.store.db.transaction() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.deleted.is_(False)).with_for_update()).mappings().first()
            if not row or row["status"] != "queued": return None
            if row["data"].get("next_attempt_at", 0) > time.time(): return None
            history = connection.execute(select(attempts.c.data).where(attempts.c.job_id == job_id)).scalars().all()
            generation = row["data"].get("processing_generation", 0)
            started = [datetime.fromisoformat(item["started_at"]).timestamp() for item in history if item.get("generation", 0) == generation]
            if started and time.time()-min(started) >= settings.processing_deadline_seconds:
                connection.execute(update(jobs).where(jobs.c.id == job_id).values(status="failed", version=row["version"]+1, data={**row["data"], "status": "failed", "error": "Processing deadline exceeded.", "updated_at": utc_now()}))
                return None
            number = (connection.execute(select(func.max(attempts.c.number)).where(attempts.c.job_id == job_id)).scalar() or 0)+1
            token = uuid.uuid4().hex
            attempt = dict(id=uuid.uuid4().hex, job_id=job_id, tenant_id=row["tenant_id"], number=number, fence=token, lease_until=time.time()+settings.worker_lease_seconds, status="running", data={"started_at": utc_now(), "generation": row["data"].get("processing_generation", 0), "pipeline_version": PIPELINE_VERSION, "schema_version": SCHEMA_VERSION, "prompt_version": PROMPT_VERSION, "model": settings.openai_model if settings.llm_provider == "openai" else settings.gemini_model})
            changed = connection.execute(update(jobs).where(jobs.c.id == job_id, jobs.c.version == row["version"], jobs.c.status == "queued").values(status="processing", version=row["version"]+1, data={**row["data"], "status": "processing", "updated_at": utc_now()}))
            if changed.rowcount != 1: return None
            connection.execute(insert(attempts).values(**attempt))
            return attempt

    def _owned(self, connection, fence):
        row = connection.execute(select(attempts).where(attempts.c.fence == fence, attempts.c.status == "running", attempts.c.lease_until > time.time())).mappings().first()
        if row is None: return None
        job = connection.execute(select(jobs).where(jobs.c.id == row["job_id"], jobs.c.deleted.is_(False), jobs.c.status == "processing").with_for_update()).mappings().first()
        if not job: return None
        locked = connection.execute(select(attempts).where(attempts.c.id == row["id"], attempts.c.status == "running", attempts.c.lease_until > time.time()).with_for_update()).mappings().first()
        return (locked, job) if locked else None

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
            connection.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(status="completed", data={**attempt["data"], "completed_at": utc_now(), "provider_usage": response.processing_summary.get("provider_usage", {})}))
            return True

    def _finish_failure(self, connection, attempt, job, retryable, error):
        generation = job["data"].get("processing_generation", 0)
        history = connection.execute(select(attempts.c.data).where(attempts.c.job_id == job["id"])).scalars().all()
        count = sum(item.get("generation", 0) == generation for item in history)
        started = min(datetime.fromisoformat(item["started_at"]).timestamp() for item in history if item.get("generation", 0) == generation)
        retry = retryable and count < settings.processing_max_attempts and time.time()-started < settings.processing_deadline_seconds
        status = "queued" if retry else "failed"
        delay = min(120, settings.retry_base_seconds*2**(count-1)) * random.uniform(0.75, 1.25)
        available_at = time.time()+delay if retry else 0
        connection.execute(update(attempts).where(attempts.c.id == attempt["id"]).values(status="retryable" if retry else "failed", data={**attempt["data"], "failure_kind": "transient" if retryable else "permanent", "finished_at": utc_now()}))
        connection.execute(update(jobs).where(jobs.c.id == job["id"]).values(status=status, version=job["version"]+1, data={**job["data"], "status": status, "error": error, "next_attempt_at": available_at, "updated_at": utc_now()}))
        if retry:
            connection.execute(insert(outbox).values(id=uuid.uuid4().hex, job_id=job["id"], tenant_id=job["tenant_id"], published=False, available_at=available_at, attempts=0))
        return retry

    def fail(self, fence, retryable=False, error="Processing failed."):
        with self.store.db.transaction() as connection:
            owned = self._owned(connection, fence)
            if not owned: return False
            return self._finish_failure(connection, *owned, retryable, error)

    def reconcile(self):
        recovered = 0
        with self.store.db.transaction() as connection:
            expired = connection.execute(select(attempts).where(attempts.c.status == "running", attempts.c.lease_until <= time.time())).mappings().all()
            for attempt in expired:
                job = connection.execute(select(jobs).where(jobs.c.id == attempt["job_id"], jobs.c.deleted.is_(False), jobs.c.status == "processing").with_for_update()).mappings().first()
                if job:
                    current = connection.execute(select(attempts).where(attempts.c.id == attempt["id"], attempts.c.status == "running", attempts.c.lease_until <= time.time()).with_for_update()).mappings().first()
                    if not current: continue
                    self._finish_failure(connection, current, job, True, "Worker lease expired.")
                    recovered += 1
        return recovered

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
