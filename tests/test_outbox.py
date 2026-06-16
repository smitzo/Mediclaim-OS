from sqlalchemy import select, update
from app.db.schema_v1 import outbox
from app.api import routes
from tests.test_tenant_access import login


def test_broker_outage_keeps_submission_and_recovers(client, pdf_bytes, monkeypatch):
    login(client)
    def offline(*_): raise ConnectionError("broker offline")
    monkeypatch.setattr(routes.process_claim_job, "delay", offline)
    response = client.post("/api/claims", data={"claim_id": "durable"}, files={"file": ("fixture.pdf", pdf_bytes)})
    assert response.status_code == 202
    job = response.json()["job"]
    assert routes.storage.get_job(job["job_id"]).status == "queued"
    with routes.storage.db.transaction() as connection:
        connection.execute(update(outbox).values(available_at=0))
    delivered = []
    assert routes.storage.dispatch_outbox(delivered.append) == 1
    assert delivered == [job["job_id"]]
    assert routes.storage.dispatch_outbox(delivered.append) == 0
