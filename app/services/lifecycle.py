"""Authorized tombstones prevent processing and restore workflows resurrecting claims."""
import hashlib
import json
import os
import shutil
import sqlite3
from pathlib import Path
from sqlalchemy import select, update, delete, insert
from fastapi import HTTPException
from app.db.schema_v1 import jobs, results, reviews, attempts, outbox, audits
from app.services.storage import utc_now


def delete_claim(store, job_id, tenant_id, actor):
    with store.db.transaction() as connection:
        row = connection.execute(select(jobs).where(jobs.c.id == job_id, jobs.c.tenant_id == tenant_id).with_for_update()).mappings().first()
        if not row: raise HTTPException(status_code=404, detail="Claim job not found.")
        key = row["object_key"]
        if not row["deleted"]:
            data = {**row["data"], "claim_id": "[deleted]", "filename": "deleted.pdf", "status": "failed", "error": None}
            connection.execute(update(jobs).where(jobs.c.id == job_id).values(deleted=True, status="failed", claim_id="[deleted]", data=data, version=row["version"]+1))
            for table in (results, reviews, audits, attempts, outbox):
                connection.execute(delete(table).where(table.c.job_id == job_id))
            import uuid
            connection.execute(insert(audits).values(id=uuid.uuid4().hex, tenant_id=tenant_id, job_id=job_id, created_at=utc_now(), data={"action": "claim_deleted", "actor": actor}))
    # The tombstone is committed first; retrying deletion safely retries object cleanup.
    if key: store.documents.delete(key)
    return {"status": "deleted", "job_id": job_id}


def deletion_ledger(store):
    with store.db.engine.connect() as connection:
        return list(connection.execute(select(jobs.c.id).where(jobs.c.deleted.is_(True))).scalars())


def create_backup(store, destination):
    if store.db.engine.dialect.name != "sqlite": raise ValueError("Use the PostgreSQL backup runbook for production databases.")
    destination = Path(destination)
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    database = destination/"claims.sqlite3"
    source = store.db.engine.raw_connection()
    try:
        with sqlite3.connect(database) as output: source.driver_connection.backup(output)
    finally: source.close()
    os.chmod(database, 0o600)
    manifest = {"version": 1, "database_sha256": hashlib.sha256(database.read_bytes()).hexdigest(), "objects": {}, "deleted_ids": deletion_ledger(store)}
    with store.db.engine.connect() as connection:
        records = connection.execute(select(jobs).where(jobs.c.deleted.is_(False))).mappings().all()
    for row in records:
        content = store.read_pdf(row["id"], row["tenant_id"])
        path = destination/"documents"/row["object_key"]
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(content); os.chmod(path, 0o600)
        manifest["objects"][row["object_key"]] = row["checksum"]
    (destination/"manifest.json").write_text(json.dumps(manifest, indent=2)); os.chmod(destination/"manifest.json", 0o600)
    return {"jobs": len(records), "objects": len(manifest["objects"])}


def restore_backup(source, target, latest_deleted_ids):
    from app.services.storage import ClaimStorage
    from app.services.documents import validate_key
    source, target = Path(source), Path(target)
    if target.exists() and any(target.iterdir()): raise ValueError("Restore target must be empty.")
    manifest = json.loads((source/"manifest.json").read_text())
    if hashlib.sha256((source/"claims.sqlite3").read_bytes()).hexdigest() != manifest["database_sha256"]: raise ValueError("Backup database checksum mismatch.")
    for key, checksum in manifest["objects"].items():
        validate_key(key)
        if hashlib.sha256((source/"documents"/key).read_bytes()).hexdigest() != checksum: raise ValueError("Backup document checksum mismatch.")
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    shutil.copy2(source/"claims.sqlite3", target/"claims.sqlite3")
    if (source/"documents").exists(): shutil.copytree(source/"documents", target/"documents")
    store = ClaimStorage(target)
    for job_id in set(latest_deleted_ids) | set(manifest["deleted_ids"]):
        with store.db.engine.connect() as connection:
            row = connection.execute(select(jobs).where(jobs.c.id == job_id)).mappings().first()
        if row: delete_claim(store, job_id, row["tenant_id"], "restore-deletion-ledger")
    return store
