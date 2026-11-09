# Sprint0 closure register — conditional review

The canonical 158-ID inventory is retained without duplicate IDs or fabricated new requirements. Its starting source is PR81 `af6d2c8243c49d60019c8fb75770a459342626d4`, `docs/verification/oc-dev-001/REQUIREMENTS_GAP_MATRIX.csv`; current source references/hashes use PR89 `ecfdff2cf3f9d1a7b7b284e79a7f708d1baea8ce`. This package is a versioned review crosswalk, **not a replacement canonical authority register**. Each row retains the historical implementation classification and approval provenance separately from the new closure disposition. Historical statuses are not silently upgraded by this review.

| Review disposition | IDs | Meaning |
|---|---:|---|
|RESOLVED|14|Bounded authority/scope/technical reconciliation resolved; owner/provider/UAT/release acceptance remains separate.|
|APPROVED_DEFERRED|25|Sequencing outside Sprint1 under the approved ten-sprint program; no waiver or automatic approval of detailed missing semantics.|
|AWAITING_OWNER_DECISION|39|Precise authority, semantic policy or final acceptance decision still required.|
|BLOCKED|80|Source recovery, external gate or incomplete whole-contract evidence remains. Includes62 unrecovered IMP definitions.|
|Total|158|Exact complete rows: CSV and JSON alongside this report.|

## Authority and scope reconciliation

AUTH-694 OptionA/Round110 remains APPROVED/CURRENT from owner-supplied conversation text. `docs/planning/authority/AUTH-694.v1.json` accurately labels the original repository approval artifact SOURCE_NOT_RECOVERED and implementation/certification/UAT separately. Validation reports33 slots,31 included,30 unrecovered included definitions and14 ordered closure steps. Journey20 Service Catalog is excluded; Journey32 Kubernetes/container observability skipped; Journey33 licensing description is recovered but its detailed authority remains pending. Do not infer the other30 numbered journey definitions from names of features. The158 requirements,33 slots and14 steps are separate crosswalk dimensions, not additive feature totals.

AUTH-491=B and AUTH-495=C selections stay preserved. Their full original wording is unrecovered; local/assumed external closure is not provider-verified closure. The range through AUTH-694 is **not** independently recovered in full. AUTH-694 registration does not fill missing historical decisions.

Current included scope: Windows/Linux host/process/service and current/history monitoring, APIs, read-only Pentaho, Email/PagerDuty, background alert/correlation/recovery and approved central PostgreSQL spool *architecture*. Excluded: ServiceNow, incident-management UI, SFTP, cloud-object-storage monitoring and Pentaho execution/mutation controls. Kubernetes workload monitoring remains excluded; deploying OpsControl itself on Kubernetes is a separate permitted packaging concept. Historical `UI-021` incident pagination is now an excluded UI requirement, not a failed missing feature. Compound OPS/ETL requirements retain background/included portions and historical evidence; no deletion of incident processing/models/migrations is proposed.

## Provenance conflicts and closure limitations

1. Original IMP-001–062 definitions remain unavailable; no fabricated text/signatures. Source recovery or explicit owner disposition is needed.
2. OC-IMP proposal rows and licensing/settings/event-policy details cannot be promoted to approved behavior from implementation presence alone.
3. Historical matrices contain superseded UI/scope wording (including mobile-first/incident UI). Current owner scope takes precedence; originals remain intact.
4. The approved CI program is recoverable at `b8c1615340828d1d3031c635fb319565dd9f222a`, but absent at its expected planning path in PR89. Its exact recovered text is retained under raw/APPROVED_CI_PROGRAM.md. That document labels its refactor Proposed; later owner authorization approved bounded changes, not every unimplemented detail or release waiver.
5. The14-step checklist is an owner-supplied supplemental tracker with explicit provenance, not a recovered original questionnaire. Step1 remains PARTIAL pending final contract/review boundaries; steps2–12 are not advanced,13–14 BLOCKED.

Nine selections RM-01/RM-04/RM-05/AM-01/CMP-01/CMP-02/API-01/OPS-03/UI-010 stay **Pending**. Historical OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING records are preserved; no new acceptance inferred. D07/D08 remain pending and genuine Pentaho qualification blocked.

Sprint0 evidence is ready for **conditional owner review**, not unconditional closure: owner must accept the explicit source-recovery quarantine, authority decision register and baseline/test limitations. Source-recovery gaps block claims of exhaustive journey certification, not safe bounded work under separately supplied authority.
