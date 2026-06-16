from sqlalchemy import select, update
from app.db.schema_v1 import sessions
import time
from app.api import routes
from tests.test_tenant_access import login


def test_hashed_revocable_sessions_and_csrf(client):
    headers, session = login(client)
    token = client.cookies["claimops_session"]
    assert "token" not in session
    with routes.auth_store.db.engine.connect() as connection:
        assert token not in str(connection.execute(select(sessions)).all())
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/auth/sign-out", headers={"X-CSRF-Token": "wrong"}).status_code == 403
    assert client.post("/api/auth/sign-out").status_code == 200
    assert client.get("/api/me", headers=headers).status_code == 401


def test_expiry_and_cross_origin_mutation(client):
    login(client)
    assert client.post("/api/auth/sign-out", headers={"Origin": "https://evil.example"}).status_code == 403
    with routes.auth_store.db.transaction() as connection:
        connection.execute(update(sessions).values(expires_at=int(time.time())-1))
    assert client.get("/api/me").status_code == 401


def test_auth_requires_csrf_bootstrap(client):
    assert client.post("/api/auth/sign-in", json={"username": "demo", "password": "demo"}, headers={"X-CSRF-Token": ""}).status_code == 403
