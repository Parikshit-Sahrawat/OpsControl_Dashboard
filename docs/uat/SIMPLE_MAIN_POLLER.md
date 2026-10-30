# Local UAT deployment from remote main (no SEC-06)

This UAT-only controller is separate from PR #75. It polls remote `main` every two minutes using a systemd timer and a dedicated checkout. It does not implement SEC-06, production-grade release certification, or rollback.

## Verified Ubuntu UAT deployment — 2026-10-30

- Service user: `parikshit`
- Dedicated checkout: `/home/parikshit/opscontrol-uat-main`
- Existing Compose project: `opscontrol-uat`
- Private UAT home: `/home/parikshit/.local/state/opscontrol/uat`
- Compose inputs, in order:
  1. `/home/parikshit/opscontrol-uat-main/docker-compose.demo.yml`
  2. `/home/parikshit/.local/state/opscontrol/uat/config/compose.override.yml`
  3. `/home/parikshit/.local/state/opscontrol/uat/config/compose.autodeploy.yml`
- The third file overrides the API command to run Uvicorn directly, bypassing Dockerfile.demo's automatic Alembic migration and demo bootstrap.
- The private credentials, packages, and gateway TLS mounts resolve under the persistent UAT home. Gateway Nginx configuration resolves under the dedicated checkout; gateway is not recreated by this controller.
- Approved migration tree: `8e53851a5472df716c747e197e9a2d83d2ac0031`
- Approved database revision: `0038_k8s_cluster_associations`
- A 78 MB `pg_dump -Fc` backup was created and archive-validated before the first manual deployment; a restore test was not performed.
- Manual application deployment passed: API/frontend HTTP 200, API healthy, worker started with zero restarts, PostgreSQL/gateway healthy.
- The controller's disabled-mode and already-deployed no-op tests passed.
- The systemd timer was enabled and confirmed active on the host.
- **End-to-end automatic deployment succeeded:** remote main commit `7b900aabed10ab51d69d4b9e2897164a924d8de1` was built and deployed on 2026-10-30 at 03:33:46 IST; API/frontend returned HTTP 200. Post-deployment worker processing and full database integrity were not independently certified.

## Deployment behavior

The controller fetches `origin/main`, compares it with the recorded deployed SHA, refuses changes to the approved migration tree, checks the effective API startup command and private mounts, checks the database's Alembic revision, then builds and updates only `api`, `worker`, and `frontend` using Compose `up -d --no-deps --no-build`. It records the target SHA only after API/frontend HTTP checks pass. It does not run `down`, delete volumes, or intentionally recreate PostgreSQL or the gateway.

## Installation and operations

The checked-in configuration is a **disabled example**; it is not the live host's activation state. Install the script to `/usr/local/lib/opscontrol/simple_main_poller.sh`, the configuration to `/etc/opscontrol-uat-main-poller.conf` (mode 0600), and the systemd units to `/etc/systemd/system/`. Review all paths and mount sources before enabling. Keep `OPSCONTROL_UAT_ENABLED=false` until initial validation and a baseline SHA are recorded in `/home/parikshit/.local/state/opscontrol/uat/deployment/main-poller/deployed.sha`.

Useful commands:

```bash
systemctl status opscontrol-uat-main-poller.timer --no-pager
sudo journalctl -u opscontrol-uat-main-poller.service -n 100 --no-pager
cat /home/parikshit/.local/state/opscontrol/uat/deployment/main-poller/deployed.sha
# Emergency pause:
sudo systemctl disable --now opscontrol-uat-main-poller.timer
```

## Limitations and safety

- This is **UAT only**, not a production release mechanism. Builds consume local host resources.
- No automatic rollback; failures can leave the checkout ahead of deployed containers. API/frontend HTTP health is not a worker readiness or functional acceptance test.
- Database migrations and bootstrap are not authorized by this controller. Schema changes require separate review, backup, migration, and baseline update.
- GitHub main changes to Compose files or startup behavior require review; the controller checks selected invariants, not all possible operational side effects.
- The controller does not self-update from GitHub: when PR changes are merged, the installed copy must be updated separately.
- The successful deployment is host-observed evidence, not proof of every future commit's compatibility.
