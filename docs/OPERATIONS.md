# ClaimOps operating guide

## Validation boundary

The local development implementation includes authenticated tenant access,
transactional records, private document adapters, an enqueue outbox, processing
leases, source-span evidence, decimal amounts, validation findings, and versioned
human reviews. Synthetic fixtures and provider stubs exercise the local contract.
They do not establish accuracy on customer documents, legal compliance, provider
availability, supported production load, or production acceptance.

`evaluation/acceptance.json` intentionally leaves customer-specific production
thresholds unset. `python scripts/evaluate_quality.py --production` exits with
status 2 while production is blocked. Set measured, owner-approved thresholds
and attach all required staging evidence before changing that gate. The current
supported evaluation profile is synthetic English text; scans require review.
Field precision/recall cover declared labeled fields. Span integrity is distinct
from semantic evidence correctness. No calibrated confidence or estimated cost is
claimed.

## Reproducible local startup

Use Python 3.12 and Node 22 or newer. Install backend dependencies from
`requirements-dev.lock` with `pip install --require-hashes -r requirements-dev.lock`.
Use `npm ci` in `frontend/`. Run frontend and API on the same hostname, e.g.
`http://localhost:3000` and `http://localhost:8000`; cookies are site scoped.
`NEXT_PUBLIC_API_BASE_URL` must match the API hostname.

Copy `.env.example` to `.env`, choose a unique `POSTGRES_PASSWORD`, and run
`docker compose up --build`. Compose migrates PostgreSQL before starting API,
worker and outbox dispatcher. Redis and PostgreSQL have no host port mappings.
The worker uses a memory/CPU limit; adjust only after the supported-load benchmark.
The dispatcher runs independently of the broker and reconciles expired leases.

For a single-process development installation, SQLite and private local files are
created under `DATA_DIR`. Start Redis, `uvicorn main:app`, the Celery worker, and
`python scripts/dispatch_outbox.py` separately. Run `alembic upgrade head` with
`DATABASE_URL` set when using PostgreSQL. Development schema creation does not
substitute for a production migration. Keep the same database and document
configuration across API, worker, dispatcher, and administrative commands.

## Authentication and API changes

Company registration creates a new tenant administrator. Administrators can add
members through `POST /api/auth/users` with username, password, and role. Uploader
can submit/retry/read; reviewer can review/read; administrator can do both and
request deletion. Permissions are loaded from current server-controlled
membership on each request. Administrators have no cross-tenant permission.

For a browser or cookie-jar API client:

1. `GET /api/auth/csrf`; retain the HttpOnly cookie and returned `csrf_token`.
2. Send `X-CSRF-Token` with registration/sign-in JSON and retain response cookies.
3. Use the **new** CSRF token returned by successful authentication for mutations.
4. Send cookies on every claim request. `GET /api/me` restores session metadata.
5. `POST /api/auth/sign-out` revokes the session. Legacy bearer/localStorage
   sessions are invalid; the dashboard clears its old localStorage entry.

Every claim endpoint, including `/api/process` and `/document`, requires a session.
A conflicting `X-Tenant-ID` is rejected. Caller-supplied reviewer identity is
ignored. Uploads accept `Idempotency-Key`; reuse returns the original job and a
changed payload returns 409. Batch keys are scoped to ordered file positions;
batches can partially succeed and are not one atomic submission.

Sessions are opaque and stored hashed, with expiry and revocation. Production
requires `APP_ENV=production`, `AUTH_COOKIE_SECURE=true`, explicit HTTPS
`ALLOWED_ORIGINS`, PostgreSQL, private S3 configuration, and a monitoring token of
at least 32 characters. TLS termination, encryption of database volumes/backups,
secret injection and rotation, and S3 bucket access policy are deployment duties.
Do not use the development Compose configuration as a production security claim.
Demo login requires `AUTH_DEMO_ENABLED=true` in development; it is always denied
in production. Set `NEXT_PUBLIC_DEMO_ENABLED=true` only for a development demo UI.

## Result and review contract

Money uses finite decimal strings, two fractional places, `ROUND_HALF_UP`, and a
0.01 reconciliation tolerance. Quantity uses Decimal. Currency must be an
explicit three-letter source code; an absent currency remains null. Retain
source values and unambiguous dates; ambiguous dates produce findings.

Execution status, validation findings, and human review decision are independent.
Source evidence records an exact literal span on a routed page or an explicit
missing/derived state. A literal match does not prove semantic correctness.
`confidence` stays null until calibration is available. Historical imported
results are preserved rather than silently rewritten.

Review writes require `expected_version` and `result_version`. A stale write
returns 409. Corrections remain separate from the original result and are checked
against section schemas. Resolve blocking findings before approval; acknowledge
remaining findings with notes. The UI preserves an unsaved draft on conflict.
Review history is append-only during normal operations. Explicit claim deletion
removes content-bearing review/audit records under the deletion policy and keeps
a minimal tombstone and deletion event.

## Legacy migration and rollback

Keep the old application stopped. Export an independent current deletion ledger,
back up legacy files and destination records, and rehearse in staging first.

```sh
python scripts/import_legacy.py legacy-data
python scripts/import_legacy.py legacy-data --target migrated-data --apply --backup-dir private-backups
```

The first command is a dry run. Apply requires a backup outside the source and an
explicit target. The importer preserves IDs and timestamps, checks document sizes,
rejects conflicting accounts/jobs and ambiguous tenant ownership, and skips
already imported records. `--tenant-map verified-map.json` resolves ownership
only from an operator-verified mapping. Legacy sessions are never imported.

Compare record counts, tenant memberships, object checksums, latest results and
reviews, and restart persistence. Keep imports read-only until reconciliation is
complete. Never resume legacy JSON writers against newer data. Use compatible
expand/contract migrations for rollback; preserve newer snapshots and keep writes
stopped if the old application cannot represent the new schema.

## Broker outage, duplicate delivery and worker loss

Accepted jobs and enqueue intents commit together. Outbox publishing retries
broker errors. A crash after publish may duplicate a message; a worker can acquire
only a queued job. A lease heartbeat preserves active ownership. Completion checks
that ownership and atomically commits a versioned result with terminal state.
The dispatcher requeues expired leases, with bounded attempts, jitter and a
deadline. A stale worker cannot commit. Provider billing is not exactly once.

In staging, interrupt Redis and submit a synthetic claim; record the accepted job
and unsent intent. Restart Redis and verify completion. Terminate a worker during
processing, wait for lease expiry/reconciliation, and verify eventual terminal
status and retained prior results. Check transient retry and permanent-failure
paths separately. Never repair stuck work by editing database statuses directly.

## Monitoring and incident response

`/health/live` reports process liveness; `/health/ready` checks database, broker and
document dependency access and returns 503 when unavailable. Readiness does not
prove worker availability or customer acceptance. `/metrics` reports shared route
counters, total latency, aggregate job states, queue age and expired leases.
Production metrics require `Authorization: Bearer <METRICS_TOKEN>` on an internal
monitoring network. Never put tokens in URLs or log document content.

Use `ops/alerts.json` as initial monitoring conditions, then set thresholds from
recorded load/recovery targets. Exercise dependency loss, queue backlog, expired
leases, failure spikes and budget exhaustion in staging. For an incident, stop
new submissions, preserve private snapshots and version metadata, isolate the
failed dependency, and verify recovery with synthetic claims before reopening.
Keep patient information and provider payloads out of routine incident logs.

## Backups, deletion and restore

Local-adapter tooling requires API, worker, dispatcher, and administrative writers
stopped. Backups are private and checksum verified; encrypt their storage and
choose backup expiry according to the approved retention policy.

```sh
python scripts/data_lifecycle.py deletion-ledger current-data > latest-deletion-ledger.json
python scripts/data_lifecycle.py backup current-data --target private-backups/snapshot --quiesced
python scripts/data_lifecycle.py restore private-backups/snapshot --target isolated-restore --latest-deletion-ledger latest-deletion-ledger.json --quiesced
```

Restore only to an empty, isolated target. Supply the **latest independent**
deletion ledger, including deletions after the snapshot; an old snapshot's ledger
alone cannot prevent resurrection. Verify counts, tenant access, checksums and
representative results before enabling access. Deleted jobs retain a minimal
server-generated identifier tombstone, cannot be retried, and cannot receive
stale worker results. Repeating deletion retries failed object cleanup safely.

For PostgreSQL, take a transaction-consistent `pg_dump` with credentials injected
through the secret manager/environment and restore with `pg_restore` into a new
database. Back up the corresponding private object inventory and checksums while
writes are quiesced. Reconcile the latest deletion ledger **before** permitting
API/worker access. This production procedure still requires a recorded staging
rehearsal; local SQLite restoration is separate evidence.

Set the customer-approved retention interval and deletion exceptions before
production. No guessed automatic retention or backup expiry policy is enabled.
