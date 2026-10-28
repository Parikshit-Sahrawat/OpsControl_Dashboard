# Automatic local Ubuntu UAT deployment (opt-in)

Workflow: `.github/workflows/local-uat-auto-deploy.yml`. Trigger: merged PR into `main` (or manual dispatch). Build occurs on a GitHub-hosted runner; the local self-hosted runner only pulls immutable images and updates application services.

## Before enabling

1. Protect `main`: require the relevant CI/security checks and reviewed PR merges. This workflow builds from the merge commit; it does not independently establish that all post-merge CI checks passed. **Do not enable automatic deployment until branch protection and post-merge release policy are approved.**
2. Register a **dedicated** GitHub Actions self-hosted Linux x64 runner with label `opscontrol-local-uat` on the Ubuntu UAT host. Treat runner access as host-level privileged access if it can invoke Docker; never assign this runner to untrusted PR workflows. Configure the runner service to start on boot.
3. Create an approved marker file `/etc/opscontrol/local-uat-runner-approved` (root-owned) only after reviewing runner isolation and access controls.
4. Configure repository variable `LOCAL_UAT_PUBLIC_API_URL` for the browser's API origin, and `LOCAL_UAT_AUTO_DEPLOY_ENABLED=true` **only after validation**. The default (unset) disables deployment.
5. Set runner service environment variables:
   - `LOCAL_UAT_BASE_COMPOSE`: absolute path to the **existing operator-owned** Compose base file. Do not use an unverified repository-generated replacement.
   - `LOCAL_UAT_PROJECT`: existing Compose project name (check `docker compose ls`).
   - `LOCAL_UAT_STATE_DIR`: private 0700 persistent directory, outside the Git checkout.
   - `LOCAL_UAT_API_URL`: API loopback origin; health path `/health/db` is appended.
   - `LOCAL_UAT_FRONTEND_URL`: frontend loopback URL.
6. Store the reviewed SHA256 digest of the current `backend/migrations` tree in `$LOCAL_UAT_STATE_DIR/approved-migration-hash`. A changed migration tree **blocks automatic deployment** until independently reviewed, backed up, and explicitly approved. Never automatically execute migrations against live UAT data.
7. Configure the `local-uat` GitHub Environment with access restrictions and required reviewers for the pilot; review policy before deciding whether routine no-migration deployments can proceed unattended. GHCR access must allow the runner to pull the images.
8. Test `workflow_dispatch` on an approved main commit with a disposable replica before allowing the first real UAT deployment.

## Safety contract

- Never run `docker compose down`, `--volumes`, `prune`, `rm`, PostgreSQL migration, or agent reinstall/re-enrollment.
- Deploy only `api`, `worker`, `frontend` with `--no-deps`; preserve DB, telemetry, identities, secrets, networks, and existing Compose project.
- Immutable GHCR digests, exact main SHA check, non-overlapping runs, and post-deploy API/frontend smoke checks.
- On failure: workflow FAIL; inspect logs and existing service state, and perform a separately authorized rollback. No automatic database downgrade.
- Smoke success does **not** constitute full UAT acceptance. Run authenticated RBAC, monitoring, telemetry, and sustained-ingestion checks before closing defects.

## Example operator checks (read-only)

```bash
docker compose ls
systemctl status actions.runner* --no-pager
stat -c '%a %U %n' "$LOCAL_UAT_STATE_DIR"
docker compose -p "$LOCAL_UAT_PROJECT" -f "$LOCAL_UAT_BASE_COMPOSE" ps
```

Do not put tokens, passwords, database backups, or agent enrollment credentials in GitHub repository variables or workflow logs.
