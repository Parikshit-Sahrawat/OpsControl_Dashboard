# DEV-05.2A.3 impact review

Technical review: Codex, 2026-10-25. **Accountable runtime/security/release reviewer:
unassigned. No supported-version transition or production approval.**

| Contract / source | Current behavior | Experimental change / verification |
|---|---|---|
| `backend/app/telemetry/configuration.py` | RUNTIME_VERSION 0.123.0; version-bound binary validation; generated HTTPS OTLP exporter and five method schemas | Staged patch selects only 0.163.2, requires its exact official version output, and disables its protobuf checkpoint encoding during validation. Generator/security policy otherwise unchanged. |
| `agent/opscontrol_agent.py` | 0.123.0 constructor, registration/heartbeat/apply contract; checksum validation; private state; rollback on failed config; supervisor service observation | Staged patch selects exactly 0.163.2 and applies the legacy encoding flag consistently to online/offline validation and runtime startup. No alternate versions are accepted. |
| `agent/service_health.py:envelope` and Agent run loop | Emits service/process/uptime OTLP separately from collector receiver; method attribution; authenticated Agent request | No changes. Actual Linux process observation and supervisor delivery persisted through TLS/API/PostgreSQL; invalid credentials, malformed and foreign-method envelopes rejected. Systemd/Windows health not certified. |
| `backend/app/telemetry/api.py` | Organization permissions; enrollment, runtime, checksum and revision checks; scoped worker identity; token rotation/revocation and receipts | No changes except the staged imported version constant. Unchanged HTTP/DB acceptance assertions reused; only expected-version fixture literals follow the staged contract. |
| `backend/app/telemetry/ingestion.py` | Auth before bounded envelope parsing; strict JSON/protobuf; method/signal scopes; tenant attribution; idempotency | Unchanged. Actual persistent evidence, malformed and conflicting-method rejection, expiry/revocation and audit checked. |
| Configured TLS/auth/egress | Credential-free HTTPS exporter origin; bearer reference from Agent; no insecure TLS; opt-in remote receivers; constrained methods/paths | No relaxation. Wrong CA/hostname, HTTP management and redirects rejected. Internal-network runner cannot reach an owned disjoint-network target. API/worker unit security contracts retained. |
| Default provisioning and shipping pins | `verification/dev052/provision_contrib.py`, installers, packaging, Dockerfiles and CI pin 0.123.0 | **Unchanged.** Separate candidate provisioner verifies 0.163.2 image/config/binary pins before use. No production feature flag or broadened allowlist. |
| Tests and fixtures | Collection, Agent lifecycle/re-enrollment, managed telemetry/access/worker tests; actual Agent API/DB probe | 53 updated-contract tests pass. The archived fixture inputs in `test_agent_v15.py` and `agent_v15_acceptance_probe.py` replace only the old version literal. Assertions, negative unknown versions and skip rules remain intact. Two new tests reject ten neighbor/prerelease/custom/old-version cases; two pin mismatch tests reject before execution/staging or offline promotion. |

`impact-inventory.txt` retains source/test references, including default version
metadata, installers, receiver contracts and supervisor delivery. The source diff
is `verification/dev052/collector_compat/experimental-0.163.2.patch`; it is applied
only to a new private archive. Normal checkout files and production guard stay
0.123.0. This is a proposed contract transition for review, not a deployed fix.

## Discovered compatibility defect and minimal remedy

The version-only experiment passed 53 unit/runtime checks but failed actual
downgrade startup after 0.163.2 wrote checkpoints. 0.123.0 reported:

> read known files from database: decoding file count: invalid character 'Ç' looking for beginning of value

The new binary advertises enabled `filelog.protobufCheckpointEncoding`. Official
Contrib v0.163.0 component sources identify it as a Beta gate and implement protobuf
versus JSON serialization. The image-label release revision's distribution manifest
is version 0.163.2 with these v0.163.0 components. Source snapshots/headers/license,
manifest, provenance URLs and hashes are retained. The initially queried Contrib
v0.163.2 source tag returned 404; the release repository manifest resolved the actual
component source version. No invented source revision or checksum was substituted.

The experimental CLI setting
`--feature-gates=-filelog.protobufCheckpointEncoding` keeps new checkpoint writes in
legacy JSON. It is applied only in the explicit 0.163.2 overlay, never to guarded
0.123.0. It changes checkpoint serialization, not TLS, egress, auth, token handling,
signal validation or monitoring semantics. Retest proves actual 0.123.0 startup
with the same generated config and populated storage. No checkpoint was deleted
to force a pass. Neighbor and prerelease version output is rejected, rather than
turning a single-version guard into a general allowlist.

This setting does **not** automatically convert already-written protobuf
checkpoints. A host previously run with default 0.163.2 needs a separately reviewed
state backup/migration/rollback procedure. The failed default-encoding experiment
is retained; resetting or abandoning state is not an approved remediation.

## Approval requests

1. Runtime/security owner: review the exact binary/image, proposed two-file diff,
   feature-gate support/lifecycle, endpoint exposure and security results.
2. Release owner: authorize a coordinated backend/Agent/installers/packaging/CI
   transition and exact final source-attested deployment manifests; define tested
   rollback/state migration and backup requirements. A config/storage startup test
   is not a complete supported control-plane rollback certification.
3. Platform/provider owners: supply approved genuine systemd/Windows targets and
   required platform criteria. Synthetic Linux fixtures do not certify them.
4. Legal owner: resolve transitive LICENSE/NOTICE, corresponding source/offer where
   applicable, redistribution assembly and application licensing decisions.

Until those gates pass and explicit review authorizes transition: **promotion
BLOCKED; guarded collector remains vulnerable; security BLOCKED; release NO-GO.**
