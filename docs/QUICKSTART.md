# OpsControl Quickstart — Learn, Install, Explore

**Audience:** Independent developers, students, self-hosters and open-source contributors.

**Current release status:** Development / technical preview. Approved PRs #25 (UI), #26 (release hardening) and #27 (ordered monitoring lifecycle) are merged into `main`. PR #27 passed all 17 checks at `c3250e0` and merged as `2b33b9f`. Controlled monitoring, security, restoration and browser evidence is available in the acceptance guides. Genuine provider validation, independent production security review and operator UAT remain separate gates.

## Recommended: run the complete application with Docker

Requirements: Git, a running Docker Engine/Desktop with Compose and BuildKit, Python 3 for private password generation, and Bash (Linux/macOS or WSL2 on Windows). You do not need host Python packages, Node.js or PostgreSQL. Ports **8000** and **5173** must be free.

```bash
git clone https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard.git
cd OpsControl_Dashboard
git switch main
git pull --ff-only origin main
bash scripts/demo-up.sh
docker compose -f docker-compose.demo.yml ps
```

For an existing checkout, preserve any local edits before switching/pulling. The startup command builds frontend/API images, starts PostgreSQL, applies migrations and creates a fictional organization and demo administrator. Wait for API startup before signing in. Open `http://127.0.0.1:5173`, use **demo-admin**, and read its generated password locally from **.demo-private/admin-password**. Keep this ignored file private; do not paste it into issues or logs. No real infrastructure or outbound incident destination is configured.

Verify startup and schema:

```bash
curl -fsS http://127.0.0.1:8000/openapi.json >/dev/null
curl -fsS http://127.0.0.1:5173/ >/dev/null
docker compose -f docker-compose.demo.yml exec -T api alembic current
```

Expected migration head: `0024_notification_leases`. Sign in and confirm the fictional **DEMO-LAB** organization in Resource Management; socket checks alone do not validate authentication. Missing observations remain unknown. The default demo does not start a monitoring worker; use the linked disposable acceptance labs for synthetic collection and alert recovery.

```bash
# Stop while preserving local database contents and the generated password.
bash scripts/demo-down.sh
# Resume with the same startup command.
bash scripts/demo-up.sh
```

API/frontend bind only to loopback and PostgreSQL has no published host port. Do not expose this development profile publicly. Avoid `down --volumes` unless you intend to erase its data. If dependency installation reports certificate errors, use your trusted organization CA through the optional ephemeral BuildKit override described in [deployment/UAT](DEPLOYMENT_UAT.md); never disable TLS verification. A read-only Docker configuration directory can be handled with a writable `BUILDX_CONFIG` outside the checkout.

The sections below describe the alternative host-based development workflow, which uses the separate `docker-compose.yml` database rather than the complete demo profile.

## What you'll learn in 10–20 minutes

- **Data Source:** A host, API, database, ETL job or other resource you want to observe.
- **Collector:** A worker that retrieves observations from a Data Source using a supported adapter.
- **Metric:** A numeric observation (availability, CPU %, runtime seconds).
- **Log:** A time-stamped event or message.
- **Alert Rule:** A condition evaluated against metrics/logs that changes alert state.
- **Monitoring Template:** A versioned configuration package. Attaching one **does not automatically start monitoring**; explicitly activate its pinned monitoring rules through Monitoring Setup.
- **Organization:** An authenticated tenant boundary enforced by backend authorization and scoped database access. The UI selector selects a view; it does not grant access.

### How the components relate

```text
React UI (http://localhost:5173)
          |
          v
FastAPI (http://localhost:8000) ------ PostgreSQL (localhost:5432)
          ^
          |
Collector Worker (optional; runs separately)
          |
     Supported adapter -> observation -> metric/log/alert evidence
```

## Prerequisites

- Git
- Docker Engine + Docker Compose plugin (only for local PostgreSQL)
- Python 3.12, with `python3` and `venv`
- Node.js 20 or compatible modern LTS and npm
- Free local ports: 5432 (PostgreSQL), 8000 (FastAPI), 5173 (Vite)

These commands are written for Linux/macOS shells. On Windows, use WSL2 or adapt the virtual-environment activation and shell commands.

## 1 — Get the source

```bash
git clone https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard.git
cd OpsControl_Dashboard
```

> **Branch note:** Use `main`. Historical staging/feature branches are already merged; do not switch to an old documentation branch.

## 2 — Start a local database

From the repository root:

```bash
docker compose up -d postgres
docker compose ps
```

The supplied Compose file runs PostgreSQL 17 with **development-only** username/password `opscontrol` and a persistent local volume. Do not reuse these credentials or publish port 5432 outside a trusted machine. This does **not** containerize the full application.

## 3 — Set up the backend

In terminal A:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` for your local environment. Keep the sample `DATABASE_URL` if using the supplied Compose database, and set `SEED_DEMO_DATA=false`. **Do not copy real production credentials into this project.** Never commit `.env`.

```bash
alembic upgrade head
alembic current
python -m scripts.create_admin --username admin
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The administrator command prompts for a new strong password and refuses to create a predictable default account. See [authentication and role guide](AUTHENTICATION.md). Sign in to the UI using this new account.

Expected: FastAPI starts. Open [http://localhost:8000/docs](http://localhost:8000/docs) to explore its interactive OpenAPI documentation, or run:

```bash
curl http://localhost:8000/
curl http://localhost:8000/openapi.json
```

If the first `alembic upgrade head` fails with a duplicate `executiontype` PostgreSQL enum, ensure your checkout is updated to current `main`, which contains the tested migration fix. Do not run a destructive database reset on a database containing anything you need.

## 4 — Start the frontend

In terminal B, from the repository root:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

The supplied frontend environment sets `VITE_API_BASE_URL=http://localhost:8000`. Open [http://localhost:5173](http://localhost:5173). If the browser reports CORS errors, ensure the backend `CORS_ORIGINS` contains the **exact** browser origin (`http://localhost:5173` by default), and that the API is running.

## 5 — Explore without connecting private infrastructure

1. Open **Overview** for scoped backend counts and clickable navigation KPIs. Missing evidence stays unknown; empty tables are expected before collection.
2. Open **ETL Jobs** to explore search, filters and execution detail layout. Real external ETL monitoring is not connected by default.
3. Open **Resource Management** to inspect Organizations, Data Sources, Collectors and Templates. Create only **fictional** organization names and test Data Sources on this trusted local instance.
4. Open **VM Health**, **APIs**, **Incidents** and **Reports** for collector evidence, local incident lifecycle and observation-based reports. Run the [Sprint 4 virtual lab](OPERATIONAL_DASHBOARDS.md) to generate actual synthetic HTTPS/ETL/host evidence and browser captures. These capabilities are merged into `main`; controlled tests remain distinct from genuine provider acceptance.
5. Browse `/docs` for schemas and endpoints. Authenticated builds require the bootstrap administrator and organization membership; configure live credentials only through supported secure references after approved provider setup. The lab needs only generated local credentials.

### Optional: worker process

The worker is a separate process and is not required just to explore the UI. In terminal C:

```bash
cd backend
source .venv/bin/activate
python -m scripts.run_collector_worker
```

It polls **enabled, supported** collectors in the database. It does not magically discover hosts or install agents. Stop with Ctrl+C. A template attachment alone does not create operational collectors. Linux, controlled EC2/Kubernetes/Windows/Carte and HTTPS adapters have runtime evidence; genuine provider acceptance is separately recorded. OTEL install registration is descriptive and remains inactive without a supported runtime adapter.

### About the existing demo seed

**Do not run `backend/scripts/seed_demo.py` for a public demo yet.** Its current fixtures include legacy environment-specific naming and have not passed the public-safe sample-data review. A neutral synthetic sample-data set is planned. You can inspect the UI with an empty database, or create fictional resources manually.

## 6 — Verify your local setup

```bash
# From any terminal
curl -f http://localhost:8000/openapi.json >/dev/null && echo "API OK"
curl -f http://localhost:5173/ >/dev/null && echo "Frontend OK"

# From repository root
docker compose ps
```

Expected: API and frontend respond, PostgreSQL is running. This verifies local startup only, **not** real monitoring, authentication, alert delivery or production security.

For reproducible integration evidence, see [Phase 1 staging verification](sdlc/08-STAGING-VERIFICATION.md) and the [verified audit](sdlc/07-CODE-AUDIT.md). Its synthetic test runs proved a manually configured HTTP collector could produce one availability metric sample; they also proved anonymous cross-tenant access and non-operational template attachment, both release blockers.

## 7 — Troubleshooting

| Symptom | First checks |
|---|---|
| `psycopg` connection refused | `docker compose ps`, port 5432, `DATABASE_URL`, database readiness |
| Duplicate PostgreSQL enum during fresh migration | Use reviewed migration fix branch; see issue #14 |
| `uvicorn` command not found | Activate `backend/.venv`, install requirements |
| Blank/failed UI API calls | API running on 8000, `VITE_API_BASE_URL`, `CORS_ORIGINS` exact origin |
| Port already in use | Stop conflicting process or adjust both service and frontend URLs |
| Dashboard shows no jobs | No real data source/collector connected; don't mistake absence of data for healthy state |
| Template attached but no samples | Expected current limitation; automatic activation is unimplemented (#3) |
| AWS/Kubernetes/OS source doesn't collect | Those adapters are proposed or incomplete; consult capability documentation rather than assuming support |

## 8 — Stop safely

Stop FastAPI, Vite and worker with Ctrl+C. From repository root:

```bash
docker compose down
```

This stops PostgreSQL and **retains** its named volume. `docker compose down -v` would delete the local database volume; use it only if you intentionally want to discard all local test data.

## 9 — Learn next and contribute

- [System architecture](sdlc/phase2/01-ARCHITECTURE.md)
- [Independent Metric, Log and Alert Rules](sdlc/phase2/09-RULE-CATALOG-DESIGN.md)
- [Infrastructure collectors](sdlc/phase2/10-INFRASTRUCTURE-COLLECTORS.md)
- [Open-source product principles](sdlc/phase2/12-OPEN-SOURCE-PRODUCT-PRINCIPLES.md)
- [Known defects and verified limitations](sdlc/07-CODE-AUDIT.md)
- [GitHub issues](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues)

Contributions should use synthetic data and generic infrastructure names. A future beginner learning path will cover **metrics → logs → alerts → collectors → dashboards → observability integrations** with safe hands-on exercises. Licensing, security policy and contribution governance are planned and must be finalized before claiming a mature open-source release.
