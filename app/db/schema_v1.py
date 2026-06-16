"""Immutable initial schema, shared by migration 0001 and repository adapters."""
from sqlalchemy import (MetaData, Table, Column, String, Integer, Float, Boolean, JSON,
                        ForeignKey, UniqueConstraint, Index, CheckConstraint)

metadata = MetaData()
tenants = Table("tenants", metadata, Column("id", String(128), primary_key=True), Column("name", String(256), nullable=False))
users = Table("users", metadata,
    Column("username", String(128), primary_key=True), Column("password_hash", String(128), nullable=False),
    Column("salt", String(64), nullable=False), Column("created_at", Integer, nullable=False))
memberships = Table("memberships", metadata,
    Column("tenant_id", ForeignKey("tenants.id"), primary_key=True),
    Column("username", ForeignKey("users.username"), primary_key=True), Column("role", String(32), nullable=False),
    CheckConstraint("role IN ('uploader', 'reviewer', 'administrator')"))
sessions = Table("sessions", metadata,
    Column("token_hash", String(64), primary_key=True), Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("username", String(128), nullable=False), Column("expires_at", Float, nullable=False, index=True),
    Column("csrf_hash", String(64), nullable=False), Column("data", JSON, nullable=False))
jobs = Table("jobs", metadata,
    Column("id", String(64), primary_key=True), Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("claim_id", String(256), nullable=False), Column("status", String(32), nullable=False),
    Column("created_at", String(64), nullable=False), Column("version", Integer, nullable=False, default=1),
    Column("deleted", Boolean, nullable=False, default=False), Column("object_key", String(512)),
    Column("checksum", String(64)), Column("data", JSON, nullable=False),
    Index("ix_jobs_tenant_created", "tenant_id", "created_at"),
    CheckConstraint("status IN ('queued','processing','succeeded','partial','failed')"))
results = Table("results", metadata,
    Column("job_id", ForeignKey("jobs.id"), primary_key=True), Column("version", Integer, primary_key=True),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False), Column("data", JSON, nullable=False))
reviews = Table("reviews", metadata,
    Column("job_id", ForeignKey("jobs.id"), primary_key=True), Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("version", Integer, nullable=False), Column("data", JSON, nullable=False))
audits = Table("audit_events", metadata,
    Column("id", String(64), primary_key=True), Column("tenant_id", ForeignKey("tenants.id"), nullable=False),
    Column("job_id", ForeignKey("jobs.id")), Column("created_at", String(64), nullable=False), Column("data", JSON, nullable=False))
outbox = Table("enqueue_outbox", metadata,
    Column("id", String(64), primary_key=True), Column("job_id", ForeignKey("jobs.id"), nullable=False),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False), Column("published", Boolean, nullable=False, default=False),
    Column("available_at", Float, nullable=False), Column("attempts", Integer, nullable=False, default=0))
attempts = Table("attempts", metadata,
    Column("id", String(64), primary_key=True), Column("job_id", ForeignKey("jobs.id"), nullable=False),
    Column("tenant_id", ForeignKey("tenants.id"), nullable=False), Column("number", Integer, nullable=False),
    Column("fence", String(64), nullable=False), Column("lease_until", Float, nullable=False),
    Column("status", String(32), nullable=False), Column("data", JSON, nullable=False),
    UniqueConstraint("job_id", "number"))
idempotency = Table("submission_keys", metadata,
    Column("tenant_id", ForeignKey("tenants.id"), primary_key=True), Column("key", String(128), primary_key=True),
    Column("fingerprint", String(64), nullable=False), Column("job_id", ForeignKey("jobs.id"), nullable=False))
auth_limits = Table("auth_limits", metadata, Column("key", String(192), primary_key=True),
    Column("window_start", Float, nullable=False), Column("count", Integer, nullable=False))
