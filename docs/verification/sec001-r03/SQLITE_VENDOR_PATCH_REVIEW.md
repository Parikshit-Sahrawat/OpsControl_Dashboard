# SEC001-R03A — SQLite CVEs: vendor-patch candidate and accountable decision

**State (2026-11-15): REVIEW REQUIRED — NOT INSTALLED, APPROVED, OR RELEASED.**
**Target:** only the two *isolated* Alpine 3.23 backend candidates on draft PR #108.
Do not alter the active Debian backend, existing eight-role image-security gate,
Grype results, or its legal status.

## Exact open findings

Both isolated Python 3.12.16 Alpine 3.23 backend candidate scans reported
**four High and zero Critical/Unknown** for `sqlite-libs 3.53.4-r0`:

| CVE | Component | Public upstream/supplier status |
|---|---|---|
| CVE-2026-119373 | FTS5 | Upstream fixed with SQLite 3.54.x; Root.io lists patched Alpine 3.23 `sqlite 3.53.4-r00072` |
| CVE-2026-119374 | FTS5 | Upstream fixed with SQLite 3.54.x; Root.io lists patched Alpine 3.23 `sqlite 3.53.4-r00072` |
| CVE-2026-119379 | session extension | Upstream fixed with SQLite 3.54.x; Root.io lists patched Alpine 3.23 `sqlite 3.53.4-r00073` |
| CVE-2026-119586 | sqlite3 command-line `.recover` output, not core engine | SQLite's upstream CVE page says this is not a core-library bug; Root.io claims a patched Alpine 3.23 `sqlite 3.53.4-r00073` |

**No official Alpine 3.23/3.24 package update has yet been verified that
resolves all four**. The upstream 3.54.1 source fixes three but does not
demonstrate closure of the `.recover` shell CVE; do not use unpatched
`3.54.1` as an assertion that all four are resolved.

Supplier disclosures:
- https://osv.dev/vulnerability/ROOT-OS-ALPINE-323-CVE-2026-119373
- https://osv.dev/vulnerability/ROOT-OS-ALPINE-323-CVE-2026-119374
- https://osv.dev/vulnerability/ROOT-OS-ALPINE-323-CVE-2026-119379
- https://osv.dev/vulnerability/ROOT-OS-ALPINE-323-CVE-2026-119586
- https://www.sqlite.org/cves.html
- https://github.com/rootio-avr/rootio_patcher

The supplier's patcher documentation requires a `ROOTIO_API_KEY` and publishes
APK packages through a **separate vendor repository**, currently AMD64-only.
These are vendor-specific patched versions, **not authoritative Alpine
security release versions**.

## Exact gated validation steps, if the owner approves this supplier

1. **Security + Platform approval BEFORE ingesting third-party APK bytes**:
   authenticate patch supplier and distribution entitlement, pin patcher
   release SHA-256 or independently verified source commit, verify repository
   key fingerprint and signed APK, capture source patches and provenance,
   approve linux/amd64-only limitation and any external API/credential exposure.
   Do not store API credentials in code, build logs, or image layers.
2. Build isolated **new**, independently named Dockerfile candidates from the
   same official digest, with only the supplier-verified `sqlite-libs` package
   replaced; bind exact APK filename, version `3.53.4-r00073`, SHA-256,
   signing key and Python `sqlite3.sqlite_version`/ABI check to the image
   evidence. A supplier claim alone does **not** establish the installed bytes.
3. Run Syft, CycloneDX, Grype and **SQLite binary-linked component verification**
   against the actual immutable candidate image. Reject unrelated transitive
   package changes, removal of the installed sqlite package to hide findings,
   unverified vendor SBOM labels or severity modification.
4. Exercise FTS5 and SQLite session-extension tests in the disposable candidate,
   verify Python's `sqlite3` C binding, backend SQLAlchemy imports, non-root
   runtime, owned PostgreSQL17 connection, complete Alembic fresh migration,
   tenant/RBAC negative paths, recovery, and original release UI/API tests.
5. Obtain **independent legal approval** for patched APK redistribution,
   modifications, attribution, source-offer and customer-self-hosted license
   duties, **bound to final SHA-256 image IDs**. Record named reviewer, dated
   signed verdict and exact scope; do not auto-create `REVIEWED`.
6. Only then nominate a final image candidate and rerun the original unchanged
   eight-role zero High/Critical/Unknown + licensing policy on the final head.

**Fail closed:** any missing patch, expired/revoked key, missing provenance,
remaining Grype severe match, incomplete compatibility suite, or missing
accountable review means **NOT ELIGIBLE**. Treat calls for risk-based treatment
as *separate*, explicit, audited decisions, never as a scanner suppression.

## Current decision

- **Installed patched Root.io APK:** NO
- **Current Alpine candidate scan:** 4 High per image
- **Original Debian backend:** UNCHANGED (severe findings remain)
- **Supplier security/platform approval:** NOT RECEIVED
- **Image-bound licence/NOTICE approval:** NOT RECEIVED
- **Customer deployment or final-image promotion:** NOT AUTHORIZED
- **Release decision:** NO-GO
