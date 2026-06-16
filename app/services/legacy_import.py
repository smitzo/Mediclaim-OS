"""Explicit, repeatable import; never infer ownership of legacy default tenants."""
import hashlib
import json
from pathlib import Path
from sqlalchemy import select, insert
from app.core.schemas import ClaimJob, ClaimResponse, ClaimReview
from app.db.schema_v1 import tenants, users, memberships, jobs, results, reviews
from app.services.documents import object_key


def inspect_legacy(source, tenant_map=None):
    source = Path(source)
    mapping = tenant_map or {}
    account_path = source/"auth"/"auth_accounts.json"
    accounts = json.loads(account_path.read_text()) if account_path.exists() else []
    known = {a["tenant_id"] for a in accounts}
    claims = []
    for path in sorted((source/"jobs").glob("*.json")):
        job = ClaimJob(**json.loads(path.read_text()))
        job.tenant_id = mapping.get(job.tenant_id, job.tenant_id)
        if job.tenant_id not in known: raise ValueError("Ambiguous legacy tenant ownership; provide a verified tenant mapping.")
        pdf = (source/"uploads"/f"{job.job_id}.pdf").read_bytes()
        if not pdf.startswith(b"%PDF"): raise ValueError("Invalid legacy PDF.")
        if job.file_size_bytes != len(pdf): raise ValueError("Legacy document size mismatch.")
        result_path, review_path = source/"results"/f"{job.job_id}.json", source/"reviews"/f"{job.job_id}.json"
        result = ClaimResponse(**json.loads(result_path.read_text())) if result_path.exists() else None
        review = ClaimReview(**json.loads(review_path.read_text())) if review_path.exists() else None
        if review and mapping.get(review.tenant_id, review.tenant_id) != job.tenant_id: raise ValueError("Review tenant ownership mismatch.")
        if review: review.tenant_id = job.tenant_id
        claims.append((job, pdf, result, review))
    return accounts, claims


def apply_import(store, accounts, claims):
    created_objects = []
    counts = {"accounts": 0, "jobs": 0, "sessions_imported": 0}
    try:
        with store.db.transaction() as connection:
            for account in accounts:
                tenant = account["tenant_id"]
                if not connection.execute(select(tenants).where(tenants.c.id == tenant)).first():
                    connection.execute(insert(tenants).values(id=tenant, name=account["company_name"]))
                previous = connection.execute(select(users).where(users.c.username == account["username"])).mappings().first()
                if previous:
                    membership = connection.execute(select(memberships).where(memberships.c.username == account["username"], memberships.c.tenant_id == tenant)).first()
                    if previous["password_hash"] != account["password_hash"] or not membership: raise ValueError("Conflicting imported account.")
                else:
                    connection.execute(insert(users).values(**{k: account[k] for k in ("username", "password_hash", "salt", "created_at")}))
                    connection.execute(insert(memberships).values(tenant_id=tenant, username=account["username"], role=account.get("role", "uploader")))
                    counts["accounts"] += 1
            for job, pdf, result, review in claims:
                checksum = hashlib.sha256(pdf).hexdigest()
                previous = connection.execute(select(jobs).where(jobs.c.id == job.job_id)).mappings().first()
                if previous:
                    if previous["tenant_id"] != job.tenant_id or previous["checksum"] != checksum or previous["claim_id"] != job.claim_id:
                        raise ValueError("Conflicting imported job.")
                    continue
                key = object_key(job.tenant_id, job.job_id)
                store.documents.put(key, pdf)
                created_objects.append(key)
                connection.execute(insert(jobs).values(id=job.job_id, tenant_id=job.tenant_id, claim_id=job.claim_id, status=job.status, created_at=job.created_at, version=1, deleted=False, object_key=key, checksum=checksum, data=job.model_dump()))
                if result: connection.execute(insert(results).values(job_id=job.job_id, tenant_id=job.tenant_id, version=1, data=result.model_dump(mode="json")))
                if review: connection.execute(insert(reviews).values(job_id=job.job_id, tenant_id=job.tenant_id, version=1, data=review.model_dump()))
                counts["jobs"] += 1
        return counts
    except Exception:
        for key in created_objects: store.documents.delete(key)
        raise
