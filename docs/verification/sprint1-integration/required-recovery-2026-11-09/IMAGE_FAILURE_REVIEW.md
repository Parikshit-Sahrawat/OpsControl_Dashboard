# Retained image-security and licence failures

Reviewed 2026-11-09 UTC (2026-11-09 Asia/Calcutta). No image publication, rebuild, waiver, suppression, threshold change or collector transition is claimed here.

Historical exact-head workflow [42588850637](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/42588850637) reports PR head `874c481a2446022b693e6660c59af15f03c5476c`. Checkout/scanner source is the synthetic merge `d63b00432f11990cc810fc9f697335c5c24e5000`, merging that head into main `2e4fe5d8cb0f39170b0d789fdd7e07be4ac0219a`. Do not relabel these as final-fix scans. API commit parent proof is recorded in BASELINE.json.

Every downloaded archive matches GitHub's SHA-256. Every scan package's CycloneDX, Syft, Grype, database, tool and licence hash matches its original provenance. Raw packages remain byte-for-byte under `hosted/image-evidence-*`; `image-summary.json` retains every High/Critical scanner match including fix state/version and advisory namespace. Counts are scanner matches, not deduplicated exploitable CVEs.

| Role | Immutable local image ID (sha256) | Critical | High | Total | Licence |
|---|---|---:|---:|---:|---|
| backend-migration | `60d8bef070ffba478a72dac46122d2dbae6c240fe6cd0ef0b343dc90aa41642d` | 0 | 59 | 186 | PENDING_ACCOUNTABLE_REVIEW |
| backend-runtime | `0937c12e145d5d1e68e00a231f0b4236d2b8140d5608aa0200cf86877b6d363e` | 0 | 59 | 186 | PENDING_ACCOUNTABLE_REVIEW |
| frontend | `fbcfdf0cb577891c6d128cb3a595a1ab20d71c4f7fe1fe2ee8afae16cce20506` | 0 | 0 | 3 | PENDING_ACCOUNTABLE_REVIEW |
| ingestion-gateway | `6d2f43e19114a873de991a76fe402bb2b882647de850e40955506fa548c9c28b` | 0 | 0 | 3 | PENDING_ACCOUNTABLE_REVIEW |
| otel-contrib | `f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97` | 19 | 81 | 178 | PENDING_ACCOUNTABLE_REVIEW |
| postgres | `548a5225a98ed6062498c769b586d2578b32c4d203a3fa16905db0444c3dab38` | 3 | 32 | 64 | PENDING_ACCOUNTABLE_REVIEW |
| uat-backend | `c515d2a7d37767dde6b805e7ccd0881079717aa49d9f741986c6d98f1d9fe38f` | 19 | 140 | 364 | PENDING_ACCOUNTABLE_REVIEW |

Total: **984 matches; 41 Critical; 371 High**. Local image configuration IDs bind the actual scan inputs; these are not registry manifest digests or authorization to publish.

## Investigation and bounded next actions

- Backend runtime and migration: each has 59 High Debian matches, all scanner-labelled `wont-fix`. This label is not an exception or proof of unreachability. Shared OS packages include util-linux libraries and perl-base. A compatible supported base/package remedy requires an independently reviewed image workstream and regression/rescan; no essential libraries were removed to conceal matches.
- PostgreSQL: all 35 Critical/High matches identify Go stdlib `go1.24.6` in `/usr/local/bin/gosu`, not PostgreSQL server source. Grype marks fixes available. The exact affected executable is part of the database image entrypoint privilege boundary. Evaluate an approved supported image shipping fixed gosu, then qualify migration, startup, backup/restore and exact-image scans. Do not replace an immutable database identity without review.
- OTel: 100 Critical/High matches; 95 scanner-labelled fixed, 3 with unspecified fix state, 2 not-fixed. Affected compiled dependencies include Go stdlib, x/crypto, x/net, gRPC and AMQP. The product remains pinned to 0.123.0; a dependency fix in a later binary does not authorize transition or certify queue/checkpoint compatibility. Qualification and accountable collector/security owners remain required.
- UAT backend: combines the OTel and Debian families, with 159 Critical/High matches (95 fixed, 59 wont-fix, 3 unspecified, 2 not-fixed). Retained as a separate role, with no unsupported exemption for UAT.
- Frontend and ingestion gateway: no Critical/High in these scans; three Medium matches each still remain in the raw results (including busybox). Both jobs remain failed because licence review is pending. No scanner result is waived.

All seven inventories have `reviewer: null`. Accountable legal/licence and engineering review must resolve component attribution, base-image obligations, NOTICE/source offers, distribution mode and the application licence decision; automated inventory is not legal clearance. Syft 1.57.0 and Grype 0.121.2 metadata are retained. Database provenance records build timestamp `2026-11-08T06:19:57Z` and schema v6.1.10; the exact archive URL/checksum is retained per role.

New-head scans will run under unchanged policy after push. Their outcome remains pending. SECURITY BLOCKED and RELEASE NO-GO remain in force.
