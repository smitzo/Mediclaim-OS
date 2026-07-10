from tests.test_tenant_access import login


def test_route_labels_and_liveness(client):
    login(client)
    client.get("/api/claims/private-identifier")
    metrics = client.get("/metrics").json()
    assert not any("private-identifier" in key for key in metrics["requests"])
    assert any("{job_id}" in key for key in metrics["requests"])
    assert client.get("/health/live").status_code == 200
    response = client.get("/health/ready")
    assert response.status_code in {200, 503}
    assert set(response.json()["checks"]) == {"database", "broker", "documents"}
