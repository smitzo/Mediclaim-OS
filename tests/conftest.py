"""Isolated API fixtures; no real claims, broker, or provider calls."""
import os
import tempfile

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="claim-tests-")
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

import fitz
import pytest
from fastapi.testclient import TestClient

from main import app
from app.api import routes
from app.core.schemas import ClaimResponse
from app.services.auth import AuthStore
from app.services.storage import ClaimStorage


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(routes, "storage", ClaimStorage(tmp_path))
    monkeypatch.setattr(routes, "auth_store", AuthStore(tmp_path / "auth"))
    monkeypatch.setattr(routes.process_claim_job, "delay", lambda *args: None)
    monkeypatch.setattr(routes, "process_claim_pdf", lambda claim_id, _: ClaimResponse(
        claim_id=claim_id, status="success", extracted_data={"identity": {"patient_name": "Synthetic Patient"}}
    ))
    with TestClient(app) as test_client:
        test_client.headers["X-CSRF-Token"] = test_client.get("/api/auth/csrf").json()["csrf_token"]
        yield test_client


@pytest.fixture
def pdf_bytes():
    with fitz.open() as document:
        document.new_page().insert_text((72, 72), "Synthetic claim fixture")
        return document.tobytes()
