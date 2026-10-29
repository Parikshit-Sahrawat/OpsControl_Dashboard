# Outbound UAT controller review, 2026-10-29

The existing SEC-01/02/03 worktree was preserved and its 59-test baseline passed.
The controller remains disabled. No live UAT services or PostgreSQL volumes were changed.

## Architecture and isolation

Use one dedicated `opscontrol-deploy` identity for release discovery, verification,
and deployment. GitHub runs only hosted publishing/build jobs. The workstation
initiates all GitHub traffic; no inbound runner or webhook listener is needed.
The authenticated inherited-FD handoff is retained, with one-use nonce reservation.
Docker socket access gives this service identity host-level authority. It must
never be shared with application processes or interactive developer sessions.

The systemd entrypoint rejects root execution and requires root-owned code and
configuration, including ancestors, without group/other writes or symlinks.
It consumes a systemd credential rather than an interactive user's GitHub login.
The token must have read-only repository/packages/attestations permissions; no
write or administration permissions are needed. Registry authentication belongs
in the dedicated private Docker configuration directory. Neither credentials nor
controller state may be mounted into application containers.

Before installation, provision `/opt/opscontrol/scripts/uat` as root-owned reviewed
code, `/etc/opscontrol-uat/controller.json` as root-owned configuration, and
`/var/lib/opscontrol-uat-deploy` as mode 0700 owned by the dedicated identity.
Configuration keys are `LOCAL_UAT_BASE_COMPOSE`, `LOCAL_UAT_OVERRIDE_COMPOSE`,
`LOCAL_UAT_PROJECT`, `LOCAL_UAT_API_URL`, `LOCAL_UAT_FRONTEND_URL`.
Provision a random 32-byte mode-0600 `handoff.key`, migration approval, and private
registry configuration. The unit references `/etc/opscontrol-uat/github-token`
through `LoadCredential`. Installation and cross-UID isolation have not been
accepted on this host; SEC-04 is not yet closed.

## Readiness and recovery

The worker writes a timestamp only after a successful scheduler/database poll.
The deployer executes its probe in the worker container and requires a heartbeat
newer than rollout start and less than 60 seconds old. API/frontend and worker
checks retry together for at most 120 seconds. No API response substitutes for
worker readiness. The disposable Docker fixture checks healthy, stale, stopped,
and recovered worker states without network access or mounted volumes.

Controller regression tests verify failed-rollout rollback, failed rollback,
preservation of the last-known-good record, and successful recovery. Those tests
mock Docker rollout. They do not constitute full SEC-06 acceptance. Full immutable
image rollout/rollback and an independently verified backup restore remain open.

## Repository gate observations

PR #75 is open on `feat/auto-uat-deploy-on-main-merge`. Its prior remote head
080a23439308d28cf09df3e32dcb3baf196badec had 17 successful checks and REVIEW_REQUIRED.
Classic main protection returned HTTP 404; active ruleset 26082467 applies.
It requires 13 Actions checks and one approval with strict status checks.
It permits four bypass actors and does not require stale-review dismissal or
last-push approval. These settings were not changed or bypassed.
The controller intentionally still rejects ruleset-based authorization until an
independent policy audit is implemented, and its trusted workflow map is empty.

Merge and activation are blocked by independent review, fresh CI on the new head,
SEC-04 host acceptance, SEC-06 full Docker/backup acceptance, and the authorization
policy gaps above. Do not enable the timer or supply live approval flags until
all these gates pass. No backup acceptance is claimed by this change.

## Local validation results

- Baseline controller/security: 59 passed.
- Expanded controller/security/recovery: 67 passed.
- Stage B contracts: 12 passed.
- Frontend Node test files: 6 passed.
- Backend disposable offline run: 547 discovered, 327 passed, 220 skipped,
  zero failures. Database integrations explicitly skip without owned PostgreSQL.
- Docker worker fault/recovery: four scenarios passed; fixture removed.

The first backend invocation mounted only backend and encountered 10 fixture/import
errors (534 discovered, 220 skipped). The corrected full-repository invocation is
recorded in backend.log; no application changes were needed to correct that setup.
Host pytest was unavailable; the repository uses unittest and the cached backend
image supplied its dependencies. The cached image test does not prove a fresh
image build, DB integration, full acceptance, or backup restoration.
