# Minimal UAT deployment from remote main (no SEC-06)

This alternative is separate from draft PR #75. It does not require SEC-06, attestations, GitHub runner, or release manifests. It is **not production-grade**.

## Behavior
A systemd timer polls `origin/main` every 2 minutes, fast-forwards a **dedicated clean checkout**, builds `api`, `worker`, `frontend`, and recreates **only those three services** with `--no-deps`. It never runs Compose `down`, changes PostgreSQL services, deletes volumes, or automatically runs migrations. It checks API/frontend HTTP health before recording the deployed SHA. A failure remains visible and retries on the next poll; there is **no automatic rollback** and **no worker-specific readiness gate**.

## One-time activation on the Ubuntu host (not performed by committing this PR)

1. Merge this PR into main after review. The host must have git, docker compose, flock, curl and a Docker-authorized service user.
2. Create a **dedicated checkout** (do not reset the development checkout):
   `git clone --branch main https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard.git /home/opsremote/opscontrol-uat-main`
3. Review actual live UAT Compose file paths, service names, ports, and bind mounts. Existing UAT paths may differ from example values. **The base Compose file's relative bind mounts resolve under the dedicated checkout**, so copy/provision required private files there or use a reviewed override with absolute host paths. Verify with `docker compose config` before first deployment.
4. Install `scripts/uat/simple_main_poller.sh` as `/usr/local/lib/opscontrol/simple_main_poller.sh`; install the example configuration at `/etc/opscontrol-uat-main-poller.conf` and edit paths/URLs. Keep `OPSCONTROL_UAT_ENABLED=false` until verified.
5. Install `deploy/uat/simple-main-poller.service` and `.timer` under `/etc/systemd/system/opscontrol-uat-main-poller.service` and `.timer`; adjust `User=` to the correct Docker-authorized account.
6. After validating configuration, set `OPSCONTROL_UAT_ENABLED=true`, then `sudo systemctl daemon-reload && sudo systemctl start opscontrol-uat-main-poller.service`. Check `journalctl -u opscontrol-uat-main-poller.service -n 100 --no-pager` and confirm PostgreSQL data survived. Then `sudo systemctl enable --now opscontrol-uat-main-poller.timer`.

**Limitations:** Builds run on the resource-constrained local host; failed builds may leave the dedicated checkout ahead of deployed services. Health checks cover API/frontend only. Compose configuration changes on main could affect services or mounts, so protect main and review all Compose changes. Database schema changes are **not** automatically migrated; a release requiring migrations must be handled separately. No claim of live deployment until host activation and end-to-end verification.
