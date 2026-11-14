# SEC001-R03 — Exact-image candidate qualification and accountable approval packet

**Date:** 2026-11-14. **Status:** CANDIDATES QUALIFIED FOR REVIEW ONLY; NO SECURITY/DBA/LEGAL APPROVAL.  
**Parent:** PR #105 head `974c46b1e80eda9c80b52a23e36a7ec055af780d` (PR-checkout synthetic merge source `421bde1e50e2cea843bf40a0e1fa620da0ecaeee`).  
**Candidate:** PR #108 stacked on #105, CI source `acb3cad64ce4baa2e8a3594d10020496b5f39017`.  
**Existing gates:** SEC001-R01 eight-image exact coverage; SEC001-R02 gosu qualification; SEC001-R06/#97 legal; SEC001-R03/#106 residual remediation. Production and release remain NO-GO.

## Real candidate builds and independent evidence

| Isolated candidate | Actual Docker config image ID | Severe Grype matches | CI evidence | Disposition |
|---|---|---:|---|---|
| PostgreSQL17 Alpine, gosu 1.19 recompiled with Go 1.27.4 | `sha256:7a4895a3b3f4e3f8013584fd9bb71ba5cc4767d15c039425de3334bae5215b3b` | **0** | [Run 43603098025, artifact 14117555195](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/43603098025/artifacts/14117555195) | Image scan clean; DBA, HA/DR, platform, supply-chain and legal review OPEN |
| Upstream OTel contrib 0.165.0 AMD64 | `sha256:1080afcdde7624998314ebd6cc707c401436f00dfbd778eb9d0466f7a2501c40` | **2 Unknown** | [Run 43603098025, artifact 14117660147](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/43603098025/artifacts/14117660147) | Scan incomplete: GO-2026-6859, GO-2026-5932; original Collector runtime 0.123.0 unchanged |

The PostgreSQL candidate compiled **upstream gosu tag 1.19** whose commit was compared exactly to `6456aaa0f3c854d199d0f037f068eb97515b7513`, using `golang:1.27.4-alpine3.23@sha256:7a93747afee80359e81dbe39c8a65037b147cada0262bf86f5b96dd06842b368`; PostgreSQL base pinned to `postgres:17-alpine@sha256:3540c0362c809df084ffac0ae69fe794515f9de92692f02178bcdce0ef0302ac`. The candidate replaces only the gosu executable, retains official PostgreSQL entrypoint, adds `gosu` Apache-2.0 source licence and Go build metadata. Disposable test validated `gosu nobody`, `gosu postgres`, PostgreSQL startup, a SQL insert and persistence across a clean container restart. **This is not** an HA/failover, populated database migration or recovery certification.

The OTel candidate was pulled as `otel/opentelemetry-collector-contrib:0.165.0@sha256:e40d61f10c9a617cca1ffd1be4d7e2b3a4b0f0001798ff07e58cabe82e618cea`, confirmed immutable upstream RepoDigest, and ran `otelcol-contrib --version`. Grype identified the remaining two Unknown findings:
- `GO-2026-6859` on Go stdlib `go1.27.3`, fixed in upstream Go 1.27.4
- `GO-2026-5932` on `golang.org/x/crypto v0.58.0`, with scanner-listed fix `v0.58.1-0.20261009181718-2f1f834330b2`

Do not change the active OTel 0.123.0 pin, cut native migration boundary, or suppress these findings until a separately built patched candidate and contract evidence exist.

## Baseline eight image identities requiring separate legal review

These are **config image IDs**, not release registry manifest digests; source is the parent PR synthetic merge mentioned above. After any rebuild, new identities require a fresh review.

| Role | Config image ID | Current licence/NOTICE status |
|---|---|---|
| backend-runtime | `sha256:f768b7b901e5ceb091080f4ea741b72b924502d508bdaf67db94d45a9b17ba51` | PENDING |
| backend-migration | `sha256:248e387965a15eb5326f51b0e31b8b9911398c9dbf495e19907cb27d3fa0cbb8` | PENDING |
| uat-backend | `sha256:cbccd5aec11b4e9af0b1108b1a7c7b9f1c786a0644eb20d74b7cf1a31828dff0` | PENDING |
| demo-frontend | `sha256:b98ca9f5533512cd6446e264845ee46c633791646018f7bddc447d477e8eadfa` | PENDING |
| postgres | `sha256:68132b6f1184562a78ebb6d063760ffff0fa796c0540292398e255145925bd35` | PENDING |
| ingestion-gateway | `sha256:c4e7e410224b2e343b4afd25c61d22b764351fdcf08d35ffcde700fce2cec637` | PENDING |
| otel-contrib | `sha256:f0eaa24275f0eac77186cf0c9b1d1c72c9edde884a7c6bf9e5332ca8b5939d97` | PENDING |
| production-frontend | `sha256:64da4855daedf6b185cd6a1f0f377922c59d671f22932d23610ba4d76f6f0aa5` | PENDING |

[Parent eight-image scan and coverage artifacts](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/43565082918).

## Accountable decisions requested — NOT RECEIVED

| Decision | Review evidence required | Accountable reviewer | State |
|---|---|---|---|
| PostgreSQL/gosu candidate | Exact gosu binary/buildinfo, source and licence, final image digest, non-root UID, extension/locale, populated migration, database backup/restore, HA quorum/fencing/failover and recovery | **DBA + Platform/Security** | PENDING ASSIGNMENT AND REVIEW |
| Collector migration candidate | Original vs candidate full configuration, authenticated transport, filelog, identity/dedupe/recovery, tested runtime interoperability and transition/rollback | **Collector architecture + Security** | PENDING ASSIGNMENT AND REVIEW |
| Debian Trixie | Source-to-binary package lists, Debian tracker dispositions, supported patches or formally evaluated exceptions; openssl package CVEs without upstream fixes stay unresolved | **Security + Platform** | PENDING ASSIGNMENT AND REVIEW |
| Full eight-image licences/NOTICE | Per-image SBOM licence expression and text, copyright, source offers, weak/copyleft obligations, modified redistributables, embedded Go module provenance, complete shipping NOTICE | **Legal/open-source compliance reviewer** | PENDING ASSIGNMENT AND REVIEW |
| GitHub PR #105 approval | Independent review with write access (author self-approval is insufficient) and final passing mandatory checks | **Independent repo writer** | PENDING ASSIGNMENT AND REVIEW |

No private or source-only artifact is an approval. No reviewer's name, date, signature or decision may be inferred or auto-written. `licenses.json` remains `PENDING_ACCOUNTABLE_REVIEW` until an accountable signature tied to the **final actual image bytes** has been verified.

## Blocking gates before any merge

1. Qualify and promote an **explicitly approved** PostgreSQL/Collector replacement into the exact eight-role image contract; do not select these disposable candidates based only on scan count.
2. Close unfixed Debian findings and the remaining OTel advisories with verified fixes or an independently documented, explicitly authorized security decision (no automatic waiver).
3. Obtain legal/NOTICE signatures tied to actual built image identities and provenance; update approval mechanism without inventing status.
4. Run the **unchanged mandatory zero-severe + accountable license** gate, full application regression, source/lint/build, migration, PostgreSQL HA/DR and browser/tenant-isolation tests on the identical final head.
5. Record independent GitHub approval; only then merge the authorized PR (no deploy, no auto-release).

**Decision:** REVIEW-ONLY / SECURITY-BLOCKED / MERGE-HOLD / RELEASE-NO-GO.
