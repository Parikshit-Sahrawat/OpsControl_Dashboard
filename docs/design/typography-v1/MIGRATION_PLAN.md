# Review-first typography migration

No implementation is authorized by this proposal. Keep all files under docs/design/typography-v1 isolated from the application build; do not import TOKENS_PROPOSED.css until owner selection and separate implementation approval.

1. Owner chooses font/scale and confirms required languages; preserve Issue90's accepted Resource Management visual baseline. Record authority without inventing UAT/release acceptance.
2. Recover reviewed WOFF2 assets/source licences, immutable hashes, source/build provenance and NOTICE packaging. Review Reserved Font Names/subsetting before generating modified assets. Define metric-compatible OS fallback and failure behaviour.
3. In a dedicated implementation PR, introduce the approved tokens, semantic text roles and a bounded literal-size/family regression policy. Establish justified exceptions; do not suppress protective/security tests or retroactively fail historical code without a migration plan.
4. Migrate one vertical Resource Management slice first: navigation, filters, table, editor, history and stale-write feedback. Preserve route hierarchy, tenant filters, authorization, data/configuration semantics and owner-approved spacing/layout except typography adjustments specifically reviewed.
5. Run PostgreSQL/FastAPI/React/Playwright with admin/operator/viewer cases, tenant switching and unsaved changes. Compare desktop1920/1440/1366 in both themes; real browser zoom100/125/150/200%, keyboard focus, reflow, labelled fields, numeric alignment and long IDs. Do not substitute CSS zoom for native browser evidence.
6. Measure real cold/warm font transfer, failure fallback, CLS and layout stability under ordinary polling/ingestion; agree budgets before making performance claims. Check screenshots and actual platform fonts, not just CSS declarations.
7. With further review, migrate Overview/KPI, VM/API, ETL read-only, logs and reports using the same roles. No later-sprint capability implementation is implied. No new scheduling/execution/incident-management controls.
8. Owner visual acceptance, independent review and applicable CI precede any merge decision. Existing security/durability/provider/release gates remain independent. Rollback removes the token import and restores prior styles/assets; no data migration is needed. Retain prior screenshots and font provenance.

Acceptance blockers: native zoom/platform tests, chosen family/scale, real-app route coverage, WOFF2 packaging/NOTICE review and runtime font-failure measurements. The current package is ready for **design discussion**, not product-wide replacement or release.
