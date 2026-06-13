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
        self._attempts: dict[str, list[float]] = {}

    def limit_auth(self, address: str, username: str) -> None:
        now = time.time()
        for key in ("ip:" + address, "user:" + _token_hash(username.strip().lower())):
            hits = [hit for hit in self._attempts.get(key, []) if hit > now - settings.auth_rate_window_seconds]
            if len(hits) >= settings.auth_rate_limit:
                raise HTTPException(status_code=429, detail="Too many authentication attempts.", headers={"Retry-After": str(settings.auth_rate_window_seconds)})
            self._attempts[key] = hits + [now]

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
            "role": "administrator",
        }
        accounts.append(account)
        self._write_json(self.accounts_path, accounts)
        return self._create_session(account, demo=False)

    def signin(self, username: str, password: str) -> AuthSession:
        username = username.strip().lower()
        if username == "demo" and password == "demo" and settings.auth_demo_enabled and settings.app_env != "production":
            account = {
                "tenant_id": "tenant-demo-bypass",
                "company_name": "Demo Claims Company",
                "username": "demo",
                "role": "administrator",
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
            raise HTTPException(status_code=401, detail="Authentication required.")
        session = self._read_json(self.sessions_path, {}).get(_token_hash(token))
        if not session or session.get("version") != 2 or session.get("expires_at", 0) <= time.time():
            raise HTTPException(status_code=401, detail="Session expired or invalid.")
        if session["demo"] and (not settings.auth_demo_enabled or settings.app_env == "production"):
            raise HTTPException(status_code=401, detail="Demo authentication is disabled.")
        # Permissions are read from current server-controlled membership, not a stale session.
        if not session["demo"]:
            account = next((a for a in self._read_json(self.accounts_path, [])
                            if a["username"] == session["username"] and a["tenant_id"] == session["tenant_id"]), None)
            if not account:
                raise HTTPException(status_code=401, detail="Account is unavailable.")
            session["role"] = account.get("role", "uploader")
        return AuthSession(token=token, **{k: v for k, v in session.items() if k not in {"version", "csrf_hash"}})

    def verify_csrf(self, token: str, csrf: str) -> bool:
        session = self._read_json(self.sessions_path, {}).get(_token_hash(token), {})
        return hmac.compare_digest(session.get("csrf_hash", ""), _token_hash(csrf))

    def signout(self, token: str | None) -> None:
        sessions = self._read_json(self.sessions_path, {})
        sessions.pop(_token_hash(token or ""), None)
        self._write_json(self.sessions_path, sessions)

    def _create_session(self, account: dict[str, Any], demo: bool) -> AuthSession:
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        session = {
            "tenant_id": account["tenant_id"], "company_name": account["company_name"],
            "username": account["username"], "role": account.get("role", "uploader"),
            "demo": demo, "expires_at": int(time.time()) + settings.auth_token_ttl_seconds,
            "csrf_hash": _token_hash(csrf), "version": 2,
        }
        sessions = {key: value for key, value in self._read_json(self.sessions_path, {}).items()
                    if value.get("version") == 2 and value.get("expires_at", 0) > time.time()}
        sessions[_token_hash(token)] = session
        self._write_json(self.sessions_path, sessions)
        return AuthSession(token=token, csrf_token=csrf, **{k: v for k, v in session.items() if k not in {"csrf_hash", "version"}})

    def _read_json(self, path: Path, fallback: Any) -> Any:
        if not path.exists():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return fallback

    def _write_json(self, path: Path, value: Any) -> None:
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def _slug(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")
    return cleaned or "tenant"


auth_store = AuthStore(Path(settings.data_dir) / "auth")
