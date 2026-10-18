# Installed-build discovery record — blank until authorized witness

Authority: [ARCH-ETL-001 V1.6 §§4, 11](../../../architecture/ARCH_ETL_001_V16.md). This is a record template, **not** evidence that an environment exists or was contacted. One record is required per exact installed build, host and collection method. Do not paste passwords, tokens, private keys, raw command arguments or unredacted logs. Link controlled evidence by immutable reference and SHA-256 under an approved store.

| Field to record | Witness entry | Gate before claiming support |
|---|---|---|
| Target/environment owner, customer ID, approved route and change window | **NOT PROVIDED** | Owner authorizes each host and live test group; customer scope is explicit. |
| Pentaho product/distribution, edition, exact version/build, installation identity | **UNKNOWN** | Capture build-native manifest/banner; no version-family inference. |
| Host OS, architecture, agent version, process/service account | **UNKNOWN** | Identify Windows/Linux build and least-privilege observation rights. |
| Java vendor, version, architecture and Pentaho compatibility declaration | **UNKNOWN** | Compare installed runtime to that distribution's documented support; do not execute ETL to discover it. |
| Kitchen path/hash and supported CLI options | **UNKNOWN** | Review exact-build documentation/configuration or an approved non-executing help/version inspection; never launch a job. |
| Pan path/hash and supported CLI options | **UNKNOWN** | Same restriction; record safe argument-redaction policy and process start epoch. |
| Pentaho Server installed? Exact base URL and documented read-only repository/scheduler/history surfaces | **UNKNOWN** | Per-endpoint, exact-build and account-permission evidence; no universal Server API assumed. |
| Carte installed? Exact URL, documented GET status paths and restart-epoch source | **UNKNOWN** | Allowlist `/kettle/status/`, `/kettle/jobStatus/`, `/kettle/transStatus/` only after build review. Running inventory is advisory. |
| Authentication scheme, credential source/reference, approval owner, rotation/revocation | **UNKNOWN** | Use provider secret manager; no credential value in docs or CLI arguments. |
| TLS certificate chain, hostname, pinned DNS/IP, firewall/proxy/private route | **UNKNOWN** | Verify chain and independent local host/CIDR policy; HTTP success alone is not trust proof. |
| Native job/transformation stable ID and metadata-export method | **UNKNOWN** | Confirm repository/native IDs; name/PID/time alone cannot establish identity. |
| Execution history/result, log, step and scheduler interfaces | **UNKNOWN** | Separate trigger/scheduler, native execution outcome, steps and downstream outcome authority. |
| Timezone, DST policy, timestamp precision, restart epoch, native execution/attempt IDs | **UNKNOWN** | Capture examples including UTC offset and ambiguous times; preserve source vs observation time. |
| Installed-build capability reviewer, evidence hashes and certification decision | **UNASSIGNED / NOT RUN** | Independent witness; documented, observed and certified states recorded separately. |

Proven code declarations are in the [compatibility matrix](PENTAHO_COMPATIBILITY_MATRIX.md). No installed Pentaho build, Java runtime, Server/Carte endpoint, credential or network route was provided for Sprint 14. The twenty RT cases remain [NOT RUN](RT001_RT020_ACCEPTANCE_MATRIX.md).
