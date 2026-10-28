# DEV-05.2A — Collector compatibility decision analysis (planning only)

**Status: BLOCKED; release NO-GO.** Evidence baseline: `9a5552edbdef9aa140c8e4ea1f2e64d92f406c09`, `2026-10-25-followup/FOLLOWUP_DECISION.md`. This document is a decision plan, not a new runtime test or approval.

## Observed comparison

| Requirement | Guarded 0.123.0 | Evaluation 0.163.2 | Decision |
|---|---|---|---|
| Current application version guard | Accepted | Rejected | Explicit application contract change required before promotion |
| Unchanged collection suite | 12/12 PASS | 11 PASS, 1 guard ERROR | Upgrade gate BLOCKED; never label 0.163.2 suite green |
| Five-method generated config and local probe | Existing supported baseline | HOST_METRICS, SERVICES, SYSLOG_RECEIVER, FILE_LOG, METRIC_SCRAPE local probe PASS | Necessary, not sufficient |
| Startup, scraping, TCP syslog, file rotation/truncation/checkpoint/restart | Existing runtime tests PASS | Unchanged actual-runtime test PASS | Preserve and rerun against exact release binary |
| Negative unknown receiver | Existing compiler/negative contracts PASS | Scoped probe rejection PASS | Preserve rejection behavior |
| Real service health | Agent supervisor envelope, not collector process scraper | Synthetic/local supervisor observer evidence only | Genuine systemd/Windows provider delivery NOT CERTIFIED |
| Security | 14 Critical / 68 High scanner matches | 0 Critical / 0 High in evaluation snapshot | Security improvement is not functional approval |
| Production OTLP auth, TLS, egress and delivery | Must remain enforced | No full authenticated end-to-end certification | BLOCKED pending test |

## Compatibility questions to resolve

1. Locate the exact version guard, supported-version metadata and any fixture that encodes 0.123.0. Document why it rejects 0.163.2; do not bypass or broaden it before approval.
2. Compare generated collector configuration against 0.163.2's canonical schema and behavior for all five methods, including receiver/exporter/component deprecations, feature gates and telemetry naming. Preserve strict negative validation.
3. Verify that the agent supervisor still emits `service_health.envelope` independently of the collector; test authenticated ingestion and rejection of invalid/unauthorized envelopes. Do not replace SERVICES with unsupported process scraping.
4. Execute exact-binary Linux acceptance: host metrics, real services, TCP syslog, file log rotation/truncation, restart/checkpoint persistence, scrape targets, network interruption and recovery. Require TLS trust, authentication, egress restrictions, non-root operation and no unexpected exposed endpoints.
5. Run unchanged suite first, then propose minimal version-specific test and application changes in a separate reviewed implementation. Keep failing unchanged-guard result as evidence. Test rollback to 0.123.0 and configuration compatibility, but do not treat rollback to a vulnerable binary as security clearance.
6. Windows and genuine provider certification remain distinct required gates; a Linux local probe does not satisfy them.

## Required implementation proposal and acceptance gate

- Produce a code-level diff identifying version guard, supported configuration generator, binary provisioning/digest, integration assertions and documentation changes. No production change is authorized by this plan.
- A security/release owner must explicitly approve a supported collector-version transition and target immutable binary/image digest.
- All unchanged tests must pass on the upgraded contract after a reviewed guard change; new cross-version, negative, authenticated end-to-end and restart tests must pass. Any legitimate old-version retirement must be documented and regression tested.
- Fresh digest-bound SBOM/Grype scan, component license/NOTICE review, provenance and deployment configuration are required. Zero scanner matches on an evaluation image is not final-image clearance.
- If any acceptance requirement is missing: **collector upgrade BLOCKED; guarded 0.123.0 remains vulnerable; release NO-GO**.

## Decision requested

Approve a *separate, scoped implementation proposal* for collector contract upgrade only after code-level impact review. Current verdict: **no upgrade approval, no version guard change, no promotion**.
