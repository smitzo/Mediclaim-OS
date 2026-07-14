"""Shared bounded metrics; never label by identifiers, query strings or raw paths."""
import logging
import time
import uuid
from datetime import datetime
from contextvars import ContextVar
from sqlalchemy import select, insert, update, func
from app.db.operations import http_metrics
from app.db.schema_v1 import jobs, attempts, outbox
from app.services.storage import storage

request_id: ContextVar[str] = ContextVar("request_id", default="-")


async def request_metrics_middleware(request, call_next):
    identifier = uuid.uuid4().hex
    token = request_id.set(identifier)
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-ID"] = identifier
        return response
    finally:
        route = request.scope.get("route")
        template = getattr(route, "path", "unmatched")
        key = f"{request.method} {template} {status}"
        try:
            with storage.db.transaction() as connection:
                old = connection.execute(select(http_metrics).where(http_metrics.c.key == key).with_for_update()).mappings().first()
                elapsed = (time.perf_counter()-started)*1000
                if old:
                    connection.execute(update(http_metrics).where(http_metrics.c.key == key).values(count=old["count"]+1, latency_ms=old["latency_ms"]+elapsed))
                else:
                    connection.execute(insert(http_metrics).values(key=key, count=1, latency_ms=elapsed))
        except Exception:
            logging.getLogger(__name__).warning("Metrics persistence unavailable")
        request_id.reset(token)


def metrics_snapshot():
    with storage.db.engine.connect() as connection:
        records = connection.execute(select(http_metrics)).mappings().all()
        states = dict(connection.execute(select(jobs.c.status, func.count()).where(jobs.c.deleted.is_(False)).group_by(jobs.c.status)).all())
        pending = connection.execute(select(func.min(jobs.c.created_at)).where(jobs.c.status == "queued", jobs.c.deleted.is_(False))).scalar()
        expired = connection.execute(select(func.count()).select_from(attempts).where(attempts.c.status == "running", attempts.c.lease_until <= time.time())).scalar()
    return {"requests": {row["key"]: row["count"] for row in records}, "latency_total_ms": {row["key"]: row["latency_ms"] for row in records}, "jobs_by_status": states, "oldest_enqueue_age_seconds": max(0, time.time()-datetime.fromisoformat(pending).timestamp()) if pending else 0, "expired_leases": expired}


def readiness():
    from redis import Redis
    from app.core.config import settings
    checks = {}
    try: storage.db.check(); checks["database"] = "ok"
    except Exception: checks["database"] = "unavailable"
    try:
        Redis.from_url(settings.celery_broker_url, socket_connect_timeout=1, socket_timeout=1).ping()
        checks["broker"] = "ok"
    except Exception: checks["broker"] = "unavailable"
    try:
        if hasattr(storage.documents, "client"):
            storage.documents.client.head_bucket(Bucket=storage.documents.bucket)
        else:
            import os
            if not os.access(storage.documents.root, os.R_OK | os.W_OK): raise OSError()
        checks["documents"] = "ok"
    except Exception: checks["documents"] = "unavailable"
    return checks
