"""File-backed company authentication for local multi-tenant demos.

This intentionally avoids external dependencies while still using salted password
hashes and opaque bearer tokens. In production, replace this boundary with a
database-backed identity service and HTTP-only sessions or signed JWTs.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.schemas import AuthSession


class AuthStore:
    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.accounts_path = self.base_dir / "auth_accounts.json"
        self.sessions_path = self.base_dir / "auth_sessions.json"

    def register(self, company_name: str, username: str, password: str) -> AuthSession:
        company_name = company_name.strip()
        username = username.strip().lower()
        if not company_name or not username or not password:
            raise HTTPException(status_code=400, detail="Company name, username, and password are required.")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
        if username == "demo":
            raise HTTPException(status_code=400, detail="The demo username is reserved.")

        accounts = self._read_json(self.accounts_path, [])
        if any(account["username"] == username for account in accounts):
            raise HTTPException(status_code=409, detail="That username is already registered.")

        salt = secrets.token_hex(16)
        account = {
            "tenant_id": f"tenant-{_slug(username)}-{secrets.token_hex(4)}",
            "company_name": company_name,
            "username": username,
            "password_hash": _hash_password(password, salt),
            "salt": salt,
            "created_at": int(time.time()),
        }
        accounts.append(account)
        self._write_json(self.accounts_path, accounts)
        return self._create_session(account, demo=False)

    def signin(self, username: str, password: str) -> AuthSession:
        username = username.strip().lower()
        if username == "demo" and password == "demo":
            account = {
                "tenant_id": "tenant-demo-bypass",
                "company_name": "Demo Claims Company",
                "username": "demo",
            }
            return self._create_session(account, demo=True)

        accounts = self._read_json(self.accounts_path, [])
        for account in accounts:
            expected = account["password_hash"]
            actual = _hash_password(password, account["salt"])
            if account["username"] == username and hmac.compare_digest(expected, actual):
                return self._create_session(account, demo=False)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid company username or password.")

    def authenticate(self, token: str | None) -> AuthSession:
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token.")
        sessions = self._read_json(self.sessions_path, {})
        session = sessions.get(token)
        if not session or session.get("expires_at", 0) < time.time():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or invalid.")
        return AuthSession(token=token, **{k: v for k, v in session.items() if k != "expires_at"})

    def signout(self, token: str | None) -> None:
        if not token:
            return
        sessions = self._read_json(self.sessions_path, {})
        sessions.pop(token, None)
        self._write_json(self.sessions_path, sessions)

    def _create_session(self, account: dict[str, Any], demo: bool) -> AuthSession:
        token = secrets.token_urlsafe(32)
        session = {
            "tenant_id": account["tenant_id"],
            "company_name": account["company_name"],
            "username": account["username"],
            "demo": demo,
            "expires_at": int(time.time()) + settings.auth_token_ttl_seconds,
        }
        sessions = self._read_json(self.sessions_path, {})
        sessions[token] = session
        self._write_json(self.sessions_path, sessions)
        return AuthSession(token=token, **{k: v for k, v in session.items() if k != "expires_at"})

    def _read_json(self, path: Path, fallback: Any) -> Any:
        if not path.exists():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return fallback

    def _write_json(self, path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _slug(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    return cleaned or "tenant"


auth_store = AuthStore(Path(settings.data_dir) / "auth")
