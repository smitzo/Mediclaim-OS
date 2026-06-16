"""Server-controlled memberships and hashed, revocable opaque sessions."""
from __future__ import annotations
import hashlib
import hmac
import secrets
import time
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.schemas import AuthSession
from app.db.database import Database
from app.db.schema_v1 import tenants, users, memberships, sessions, auth_limits


def _token_hash(token): return hashlib.sha256(token.encode()).hexdigest()


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()


class AuthStore:
    def __init__(self, base_dir: str | Path, database: Database | None = None):
        self.db = database or Database(settings.database_url or f"sqlite:///{Path(settings.data_dir)}/claims.sqlite3", initialize=settings.app_env != "production")

    def limit_auth(self, address, username):
        now = time.time()
        with self.db.transaction() as connection:
            for key in ("ip:"+address, "user:"+_token_hash(username.strip().lower())):
                row = connection.execute(select(auth_limits).where(auth_limits.c.key == key)).mappings().first()
                if row and row["window_start"] > now-settings.auth_rate_window_seconds:
                    if row["count"] >= settings.auth_rate_limit:
                        raise HTTPException(status_code=429, detail="Too many authentication attempts.", headers={"Retry-After": str(settings.auth_rate_window_seconds)})
                    connection.execute(update(auth_limits).where(auth_limits.c.key == key).values(count=row["count"]+1))
                elif row:
                    connection.execute(update(auth_limits).where(auth_limits.c.key == key).values(count=1, window_start=now))
                else:
                    connection.execute(insert(auth_limits).values(key=key, count=1, window_start=now))

    def _new_user(self, connection, username, password):
        if not username or username == "demo" or len(username) > 128 or len(password) < 8 or len(password) > 1024:
            raise HTTPException(status_code=400, detail="Use a valid username and a password of 8–1024 characters.")
        salt = secrets.token_hex(16)
        connection.execute(insert(users).values(username=username, salt=salt, password_hash=_hash_password(password, salt), created_at=int(time.time())))

    def register(self, company_name, username, password):
        username, company_name = username.strip().lower(), company_name.strip()
        if not company_name or len(company_name) > 256: raise HTTPException(status_code=400, detail="Company name is required (maximum 256 characters).")
        tenant_id = "tenant-"+secrets.token_hex(16)
        try:
            with self.db.transaction() as connection:
                self._new_user(connection, username, password)
                connection.execute(insert(tenants).values(id=tenant_id, name=company_name))
                connection.execute(insert(memberships).values(tenant_id=tenant_id, username=username, role="administrator"))
                return self._create_session(connection, dict(tenant_id=tenant_id, company_name=company_name, username=username, role="administrator"), False)
        except IntegrityError:
            raise HTTPException(status_code=409, detail="That username is already registered.")

    def add_member(self, principal, username, password, role):
        username = username.strip().lower()
        if principal.role != "administrator": raise HTTPException(status_code=403, detail="Administrator permission required.")
        try:
            with self.db.transaction() as connection:
                self._new_user(connection, username, password)
                connection.execute(insert(memberships).values(tenant_id=principal.tenant_id, username=username, role=role))
            return {"username": username, "role": role}
        except IntegrityError:
            raise HTTPException(status_code=409, detail="That username is already registered.")

    def signin(self, username, password):
        username = username.strip().lower()
        with self.db.transaction() as connection:
            if username == "demo" and password == "demo" and settings.auth_demo_enabled and settings.app_env != "production":
                if not connection.execute(select(tenants).where(tenants.c.id == "tenant-demo-bypass")).first():
                    connection.execute(insert(tenants).values(id="tenant-demo-bypass", name="Demo Claims Company"))
                return self._create_session(connection, dict(tenant_id="tenant-demo-bypass", company_name="Demo Claims Company", username="demo", role="administrator"), True)
            row = connection.execute(select(users, memberships.c.tenant_id, memberships.c.role, tenants.c.name.label("company_name")).join(memberships, users.c.username == memberships.c.username).join(tenants, tenants.c.id == memberships.c.tenant_id).where(users.c.username == username)).mappings().first()
            expected = row["password_hash"] if row else "0"*64
            actual = _hash_password(password, row["salt"] if row else "0"*32)
            if row is None or not hmac.compare_digest(expected, actual):
                raise HTTPException(status_code=401, detail="Invalid company username or password.")
            return self._create_session(connection, row, False)

    def authenticate(self, token):
        if not token: raise HTTPException(status_code=401, detail="Authentication required.")
        with self.db.engine.connect() as connection:
            row = connection.execute(select(sessions).where(sessions.c.token_hash == _token_hash(token), sessions.c.expires_at > time.time())).mappings().first()
            if row is None: raise HTTPException(status_code=401, detail="Session expired or invalid.")
            data = dict(row["data"])
            if data["demo"]:
                if not settings.auth_demo_enabled or settings.app_env == "production":
                    raise HTTPException(status_code=401, detail="Demo authentication is disabled.")
            else:
                role = connection.execute(select(memberships.c.role).where(memberships.c.username == row["username"], memberships.c.tenant_id == row["tenant_id"])).scalar()
                if role is None: raise HTTPException(status_code=401, detail="Account is unavailable.")
                data["role"] = role
            return AuthSession(token=token, expires_at=int(row["expires_at"]), **data)

    def verify_csrf(self, token, csrf):
        with self.db.engine.connect() as connection:
            expected = connection.execute(select(sessions.c.csrf_hash).where(sessions.c.token_hash == _token_hash(token), sessions.c.expires_at > time.time())).scalar()
            return bool(expected) and hmac.compare_digest(expected, _token_hash(csrf))

    def signout(self, token):
        with self.db.transaction() as connection:
            connection.execute(delete(sessions).where(sessions.c.token_hash == _token_hash(token or "")))

    def _create_session(self, connection, account, demo):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        expires = int(time.time())+settings.auth_token_ttl_seconds
        data = {key: account[key] for key in ("tenant_id", "company_name", "username", "role")}
        data["demo"] = demo
        connection.execute(delete(sessions).where(sessions.c.expires_at <= time.time()))
        connection.execute(insert(sessions).values(token_hash=_token_hash(token), tenant_id=account["tenant_id"], username=account["username"], expires_at=expires, csrf_hash=_token_hash(csrf), data=data))
        return AuthSession(token=token, csrf_token=csrf, expires_at=expires, **data)


auth_store = AuthStore(Path(settings.data_dir)/"auth")
