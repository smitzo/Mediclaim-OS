"""Durable file-backed storage for claim jobs and results.

The implementation intentionally uses simple files so the project runs locally
without a database. In production, this boundary can be swapped for Postgres and
object storage without changing API routes or worker orchestration.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from app.core.config import settings
from app.core.schemas import ClaimJob, ClaimResponse, JobStatus


SAFE_NAME = re.compile(r"[^A-Za-z0-9_.-]+")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaimStorage:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.upload_dir = self.base_dir / "uploads"
        self.job_dir = self.base_dir / "jobs"
        self.result_dir = self.base_dir / "results"
        for directory in (self.upload_dir, self.job_dir, self.result_dir):
            directory.mkdir(parents=True, exist_ok=True)

    def create_job(self, claim_id: str, filename: str, pdf_bytes: bytes, page_count: int, tenant_id: str = "default") -> ClaimJob:
        now = utc_now()
        job_id = uuid.uuid4().hex
        safe_filename = _safe_filename(filename or f"{claim_id}.pdf")
        job = ClaimJob(
            job_id=job_id,
            tenant_id=_safe_identifier(tenant_id or "default"),
            claim_id=claim_id,
            filename=safe_filename,
            status="queued",
            created_at=now,
            updated_at=now,
            page_count=page_count,
            file_size_bytes=len(pdf_bytes),
            result_url=f"/api/claims/{job_id}/result",
        )
        self.pdf_path(job_id).write_bytes(pdf_bytes)
        self.save_job(job)
        return job

    def get_job(self, job_id: str) -> ClaimJob:
        path = self.job_path(job_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Claim job not found.")
        return ClaimJob(**json.loads(path.read_text(encoding="utf-8")))

    def list_jobs(self, limit: int = 100, tenant_id: str | None = None) -> list[ClaimJob]:
        jobs: list[ClaimJob] = []
        safe_tenant_id = _safe_identifier(tenant_id) if tenant_id else None
        for path in sorted(self.job_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                job = ClaimJob(**json.loads(path.read_text(encoding="utf-8")))
            except Exception:
                continue
            if safe_tenant_id and job.tenant_id != safe_tenant_id:
                continue
            jobs.append(job)
            if len(jobs) >= limit:
                break
        return jobs

    def save_job(self, job: ClaimJob) -> None:
        job.updated_at = utc_now()
        self.job_path(job.job_id).write_text(
            json.dumps(job.model_dump(), indent=2),
            encoding="utf-8",
        )

    def update_job(self, job_id: str, status: JobStatus, error: str | None = None) -> ClaimJob:
        job = self.get_job(job_id)
        job.status = status
        job.error = error
        self.save_job(job)
        return job

    def save_result(self, job_id: str, response: ClaimResponse) -> None:
        self.result_path(job_id).write_text(
            response.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def get_result(self, job_id: str, tenant_id: str | None = None) -> ClaimResponse:
        job = self.get_job(job_id)
        if tenant_id and job.tenant_id != _safe_identifier(tenant_id):
            raise HTTPException(status_code=404, detail="Claim job not found.")
        path = self.result_path(job_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Claim result is not ready yet.")
        return ClaimResponse(**json.loads(path.read_text(encoding="utf-8")))

    def read_pdf(self, job_id: str) -> bytes:
        path = self.pdf_path(job_id)
        if not path.exists():
            raise FileNotFoundError(f"Uploaded PDF for job {job_id} is missing")
        return path.read_bytes()

    def job_path(self, job_id: str) -> Path:
        return self.job_dir / f"{_safe_identifier(job_id)}.json"

    def pdf_path(self, job_id: str) -> Path:
        return self.upload_dir / f"{_safe_identifier(job_id)}.pdf"

    def result_path(self, job_id: str) -> Path:
        return self.result_dir / f"{_safe_identifier(job_id)}.json"


def _safe_identifier(value: str) -> str:
    cleaned = SAFE_NAME.sub("-", value).strip(".-")
    if not cleaned:
        raise ValueError("Identifier cannot be empty.")
    return cleaned


def _safe_filename(value: str) -> str:
    cleaned = SAFE_NAME.sub("-", value).strip(".-")
    return cleaned or "claim.pdf"


storage = ClaimStorage(settings.data_dir)


def response_to_jsonable(response: ClaimResponse) -> dict[str, Any]:
    return json.loads(response.model_dump_json())
