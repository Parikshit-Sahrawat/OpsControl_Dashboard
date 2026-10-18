# Sprint 14 — installed-build acceptance preparation

**Status: DELIVERED AS PREPARATION; REAL PENTAHO ACCEPTANCE NOT RUN. Production NOT READY.** This sprint inspected adapter safety and assembled a witnessed, read-only procedure. No Pentaho target, exact build, approved route, credentials, evidence store or live test-group authorization was supplied. No host was contacted and no ETL workload was executed.

The [approved ARCH-ETL-001 §11 R1 coverage index](../../../architecture/ARCH_ETL_001_V16.md) supplies all twenty RT labels and coverage strings. It expressly identifies them as a reconstructed working index because the original verbatim case definitions are unavailable. The [RT-001–RT-020 matrix](RT001_RT020_ACCEPTANCE_MATRIX.md) copies that coverage exactly and leaves **20/20 NOT RUN**, with witness unassigned. The proposed test procedures are preparation, not evidence or new approved requirements.

## Delivered preparation

The [discovery record](INSTALLED_BUILD_DISCOVERY.md) requests exact product/build, OS/Java, Kitchen/Pan options, native IDs, Server/Carte interfaces, timestamps, auth and TLS without pretending to know them. The [compatibility matrix](PENTAHO_COMPATIBILITY_MATRIX.md) distinguishes code-declared candidate version families from installed-build proof. The [read-only runbook](READ_ONLY_CONNECTION_RUNBOOK.md) and [credential/network prerequisites](CREDENTIAL_AND_NETWORK_PREREQUISITES.md) gate any later connection by owner authorization, scoped identity, TLS, read-only paths and approved evidence handling.

Code inspection covered the Kitchen/Pan and Server observation normalizers, R1 Carte GET reader, legacy Carte reader, capability contracts, collection bridge, credential and egress controls. Focused controlled tests passed **77/77**: 55 adapter/surface tests and 22 execution, review, history and incident contracts. These are unit/contract results, not installed-build acceptance; see [test results](TEST_RESULTS.md) and [verification](VERIFICATION.md). No runtime code, migration, production setting or approved architecture document was changed.

The [safety audit](ADAPTER_SAFETY_AUDIT.md) records **S14-01, a reproducible code-level legacy Carte outcome defect**: an XML `Finished` status without `nr_errors` is projected as `SUCCESS` by the legacy parser, while the R1 parser retains `UNKNOWN`. Legacy success claims therefore require a separately authorized scoped fix and regression before native acceptance. R1 paths and transport controls passed fixture tests; actual Server/Carte behavior, source authority, CA, network and exact-build compatibility remain unknown. Process exit zero and HTTP 200 are never native success proof.

## Remaining gates

The owner must provide and authorize the target/environment, exact installed distribution/build and read-only method, host/route, secure credential reference, evidence location/retention, and each live test group with an independent witness. Do not paste secrets into documents. The original verbatim RT case document remains unavailable; the R1 reconstructed index is the planning authority until separately superseded. S14-01 needs a scoped implementation decision. P0-03 positive shared-resource visibility, production trust/certificate lifecycle, telemetry continuity and full DR evidence remain unresolved. [Production readiness](PRODUCTION_READINESS.md) retains all 16 P0–P2 gaps and the eight audit findings. Sprint 13 backup/restore results remain local-only; the 62 historical IMP definitions remain SOURCE_NOT_RECOVERED and all 18 OC-IMP V2.0 entries remain individually unapproved.

No PR, merge, deployment, production-data change or Sprint 15 work occurred. This package does not certify Pentaho or release readiness.
