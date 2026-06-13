import pytest
from pydantic import ValidationError
from app.core.config import Settings, settings


def test_production_requires_safe_session_configuration():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, app_env="production")
    config = Settings(_env_file=None, app_env="production", allowed_origins="https://claims.example", auth_cookie_secure=True)
    assert not config.auth_demo_enabled


def test_demo_denied_by_default_and_in_production(client, monkeypatch):
    assert client.post("/api/auth/sign-in", json={"username": "demo", "password": "demo"}).status_code == 401
    monkeypatch.setattr(settings, "auth_demo_enabled", True)
    response = client.post("/api/auth/sign-in", json={"username": "demo", "password": "demo"})
    assert response.status_code == 200
    client.headers["X-CSRF-Token"] = response.json()["csrf_token"]
    monkeypatch.setattr(settings, "app_env", "production")
    assert client.get("/api/me").status_code == 401
    assert client.post("/api/auth/sign-in", json={"username": "demo", "password": "demo"}).status_code == 401


def test_authentication_throttle(client, monkeypatch):
    monkeypatch.setattr(settings, "auth_rate_limit", 2)
    for _ in range(2):
        assert client.post("/api/auth/sign-in", json={"username": "wrong", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/sign-in", json={"username": "another", "password": "wrong"}).status_code == 429
