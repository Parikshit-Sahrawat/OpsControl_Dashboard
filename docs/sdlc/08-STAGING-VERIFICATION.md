# DOC-08 — Executable Staging Verification

**Status:** Provisioned as an ephemeral GitHub Actions workflow; first execution pending.

## Environment
`.github/workflows/phase1-staging.yml` creates an isolated Ubuntu runner and PostgreSQL 17 service for each pull request or manual run. The workflow installs backend requirements, compiles and imports FastAPI/SQLAlchemy, applies all Alembic revisions, checks key tables, starts Uvicorn, checks OpenAPI and captures anonymous endpoint response codes. A separate job installs and builds the React frontend. API logs and a `tenant-baseline.json` evidence artifact are uploaded.

The workflow uses a disposable PostgreSQL database, not production credentials or a shared database. This is an **automated integration smoke environment**, not a publicly accessible staging deployment.

## Trigger
1. Push changes to `docs/sdlc-phase-1` with an open pull request (the `pull_request` event).
2. Or open GitHub Actions → **Phase 1 Staging Verification** → **Run workflow**, selecting the review branch. Workflow-dispatch visibility may require the workflow to exist on the default branch first; use the pull request trigger while it is review-only.
3. Review the **staging-smoke** and **frontend-build** jobs and download `phase1-staging-evidence`.
4. Record run URL, SHA, migration result, API startup status, tenant baseline and any failures in DOC-07 before SRS approval.

## What is proven when green
- Dependencies install on a clean runner.
- Python compiles, ORM mappers configure and the FastAPI app imports.
- Alembic `upgrade head` works against a fresh PostgreSQL 17 database and expected tables exist.
- Uvicorn serves OpenAPI including the organization route.
- React production build completes.

## What is NOT proven
- **Tenant isolation:** the workflow probes anonymous GET status codes only. A `200` response means an endpoint is publicly accessible; a `401/403` does not establish that users A and B are isolated. Authenticated multi-tenant negative tests remain missing because identity and role enforcement are not implemented.
- **Template-to-sample:** no real adapter or metric fixture is yet exercised. An OTEL collector is registered by onboarding but is unsupported by the worker.
- **Screenshots:** no browser runner or visual comparison is configured. SVG assets remain illustrations.
- **Full tests/lint:** there is no backend pytest suite or frontend lint configuration yet.
- **Migration reversibility:** downgrade tests are not included; run only in a second disposable database if approved.

## Local equivalent
```bash
git checkout docs/sdlc-phase-1
docker compose up -d postgres
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
alembic current
uvicorn app.main:app --host 127.0.0.1 --port 8000
# Separate terminal:
cd frontend
npm ci
npm run dev
```
Defaults: PostgreSQL on localhost:5432, API localhost:8000, Vite localhost:5173. The existing `docker-compose.yml` maps port 5432 on the host and uses development credentials; do not expose this instance publicly or run it on a shared production host.

## Release gate
Do not approve Phase 1 solely because the workflow passes. Require true two-tenant authorization tests, supported collector-to-sample test, real browser captures, and reviewed SRS exceptions. Never classify diagnostic-only checks as passed security tests.
