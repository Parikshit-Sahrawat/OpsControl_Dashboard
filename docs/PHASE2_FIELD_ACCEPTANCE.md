# OpsControl Phase 2 — Field Acceptance and Release Evidence

**Date:** 2026-10-10  
**Branch:** `feat/phase2-field-acceptance-ux`; [draft PR #22](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/22).  
**Safety:** CI uses fictional identities, disposable PostgreSQL, Docker-internal TLS targets and disposable kind. Neither the feature branch nor any parent draft PR is merged into `main`; no production deployment is authorized.

## Scope and evidence

| Acceptance requirement | Evidence / test | Accurate status |
|---|---|---|
| HTTP activation → leased job → **real private TLS** GET → metric → alert OPEN on HTTP 503 → RESOLVED after recovery | [Live Private HTTPS Alert and Recovery](../.github/workflows/live-http-alert-recovery.yml), `scripts/live_https_acceptance.py`, `deploy/fixtures/agent_cycle.py` | **Passed on prior commit**; includes real worker/result DB path and two isolated Docker networks |
| Private target TLS trust, no redirect, 200 → 503 → 200 detection | [Private HTTPS Target Acceptance](../.github/workflows/private-https-acceptance.yml) | **Passed on prior commit**; repeat on latest HEAD |
| Carte read-only status over actual TLS | Same workflow plus `deploy/fixtures/probe_private_carte.py` | **Synthetic Carte-shaped TLS fixture** (Running, Failed, Success) — not a genuine Pentaho Carte installation |
| Auth roles, organization isolation, schema denial, replay protection, immutable rule versioning | [Security Release Gate](../.github/workflows/phase1-staging.yml) | Automated disposable DB/browser checks; **independent threat-model review pending** |
| Nonempty existing PostgreSQL database migrates without losing owned resources | `backend/scripts/existing_database_upgrade_probe.py` downgrades to 0016, seeds Organization/DataSource, upgrades to 0018, verifies identities unchanged | **CI verification required on latest HEAD**; not an upgrade of a real deployed OpsControl database |
| Secrets: no raw credentials, scoped production provider | `backend/scripts/secrets_provider_probe.py`, `app/worker/credentials.py` | AWS Secrets Manager ARN reference + workload identity code and fake-client negatives; **live AWS Secrets Manager access not yet verified** |
| Kubernetes NetworkPolicy real enforcement | [kind+Calico CI](../.github/workflows/kubernetes-cni-acceptance.yml), `scripts/verify-cni-egress.sh` | Disposable enforcing CNI tests approved Pod reachable / denied Pod blocked; **not verified on customer's production CNI** |
| Kubernetes Pod/Deployment real API and read-only RBAC | Same kind+Calico job, `scripts/verify-kubernetes-provider.sh` | Disposable cluster acceptance added; watch latest-head run. Not a production Kubernetes cluster |
| AWS EC2 least-privilege IAM and CloudWatch status | [AWS OIDC manual acceptance](../.github/workflows/aws-ec2-live-acceptance.yml), [minimal policy](../deploy/examples/aws-ec2-monitoring-readonly-policy.json) | **NOT RUN**: requires an authorized sandbox account, scoped OIDC role and instance |
| Pentaho Carte genuine read-only job collection | `app/worker/pentaho_status.py` and `provider_unit_probe.py` | Mock/XML + synthetic TLS fixture only; **NOT verified against actual Carte** |
| Rule-version editing, activation progression, worker diagnostics and friendly errors | `frontend/src/pages/MonitoringSetup.jsx`, `backend/app/api/monitoring_diagnostics.py` | Code committed; frontend compile/Playwright and authenticated tests required on latest SHA |
| Linux host/process, Apache mod_status and Tomcat JVM | `app/worker/deep_checks.py`, `backend/scripts/deep_checks_probe.py` | Read-only adapters + synthetic safety tests. **Real service installations pending** |

## Operational controls that still block production

1. External security review of all monitoring, authentication and resource scoping, including inter-service tokens, rules, case-specific logs and SQL direct access.
2. Network-layer enforcement must be validated **in the deployment CNI or host firewall**. A passing Docker/kind test proves only the test networks, not arbitrary customer networks.
3. Complete secret migration/rotation, production workload identity review, vault policy and secret retention/audit. The credential helper supports AWS Secrets Manager but no provider account is connected here.
4. True AWS/Carte provider field tests require operator-approved temporary access or an explicitly provisioned sandbox. Tests should fail (not skip as pass) if the provider is missing when the field test is requested.
5. API/static site TLS, disaster recovery, backups, nonempty real-data migration, load/performance, alert notifications and incident-response review remain release gates.

## Reproduce without any customer data

- `bash scripts/demo-up.sh`: synthetic localhost application and DB.
- GitHub Actions on PR: test real HTTPS/alert recovery, Docker egress, kind/Calico if enabled, security/staging and build.
- Run the manual AWS acceptance only after configuring GitHub Environment `aws-acceptance` with `OPSCONTROL_AWS_ACCEPTANCE_ROLE_ARN` whose trust policy restricts this repository and environment.
- For a real Pentaho instance, deploy an independent **disposable** Carte node and give its collector a credential reference and exact hostname/CIDR, then verify the read-only adapter against that node. Never place production credentials or internal endpoint details into a public issue.

## SDLC decision

**Current stage:** Phase 2 implementation with substantial Phase 3 disposable-environment integration verification. **Not Phase 4 production security approval or Phase 5 deployment.** Requirements are not “successfully completed” until their specific environment and threat-model acceptance gates are evidenced. The [living roadmap](IMPLEMENTATION_ROADMAP.md) must remain aligned.
