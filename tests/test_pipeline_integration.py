import json
from pathlib import Path
import fitz
from app.api import routes
from app.workers import tasks
from app.services.processor import process_claim_pdf
from tests.test_tenant_access import login


def synthetic_pdf(case_index=0):
    case = json.loads(Path("evaluation/synthetic_claims.json").read_text())["cases"][case_index]
    with fitz.open() as pdf:
        for document in case["documents"]:
            pdf.new_page().insert_textbox(fitz.Rect(50, 50, 550, 750), document["text"], fontsize=11)
        return pdf.tobytes()


def test_real_graph_worker_api_and_review_without_external_calls(client, monkeypatch):
    login(client)
    monkeypatch.setattr(tasks, "storage", routes.storage)
    monkeypatch.setattr(tasks, "process_claim_pdf", process_claim_pdf)
    def forbidden(*args, **kwargs): raise AssertionError("Complete synthetic text should not require a provider.")
    for module in ("app.agents.id_agent", "app.agents.discharge_agent", "app.agents.bill_agent", "app.agents.segregator"):
        monkeypatch.setattr(module+".call_llm_json", forbidden)
        monkeypatch.setattr(module+".call_llm_json_text_only", forbidden)
    response = client.post("/api/claims", data={"claim_id": "Synthetic Integration"}, files={"file": ("synthetic.pdf", synthetic_pdf())})
    assert response.status_code == 202
    job = response.json()["job"]["job_id"]
    assert tasks.process_claim_job.run(job)["status"] == "completed"
    assert tasks.process_claim_job.run(job)["status"] == "ignored"
    result = client.get(f"/api/claims/{job}/result").json()
    assert result["extracted_data"]["itemized_bill"]["total_amount"] == "0.30"
    assert len(result["extracted_data"]["itemized_bill"]["line_items"]) == 2
    assert result["processing_summary"]["provider_usage"]["calls"] == 0
    assert not result["validation_findings"], result["validation_findings"]
    response = client.put(f"/api/claims/{job}/review", json={"expected_version": 0, "result_version": 1, "status": "approved"})
    assert response.status_code == 200, response.text
    assert response.json()["reviewer"] == "alpha"
    assert client.get(f"/api/claims/{job}/document").content.startswith(b"%PDF")


def test_conflicting_complete_documents_require_review():
    result = process_claim_pdf("Synthetic contradictory claim", synthetic_pdf(1))
    assert result.status == "success"
    assert result.processing_summary["quality"]["requires_review"]
    assert "patient_mismatch" in {finding.code for finding in result.validation_findings}
