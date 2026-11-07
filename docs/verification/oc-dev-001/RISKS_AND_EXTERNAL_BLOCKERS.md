# Risks, decisions and external blockers

## Preserved invariants

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**

Production collector0.123.0 pin/guards unchanged. Centralized PostgreSQL durable-spool direction is the current owner instruction; no alternative queue/fork/replay-primary design is selected. Exact prior spool transaction/retention specification was not located in bounded current architecture/planning/source searches;201 recovers detail without treating missing text as permission to redesign. Existing telemetry_receipts is payload-hash batch dedup; pipeline evidence/checkpoint atomicity is not end-to-end zero-loss proof.

D01–D06 approved scope is preserved; D07/D08 Pending. Genuine Pentaho qualification BLOCKED. All nine current acceptance selections RM01/RM04/RM05/AM01/CMP01/CMP02/API01/OPS03/UI010 remain Pending; historical OWNER_APPROVED_CONTROLLED_SCOPE — INDEPENDENT_UAT_PENDING remains unchanged. New verification never grants owner, security, DBA, legal or provider signatures. PR80 stays draft/unmerged.

## Prioritized unresolved boundaries

| Risk | Evidence | Prerequisite / accountable role | Impact |
|---|---|---|---|
| CHK001 accepted telemetry loss | main DEV052 queue/durability decisions; guarded0.123 delivered257/267 (10 missing), newer partial recovery9 missing; replay267/267 is historical bounded evidence, not current primary design approval | Runtime/data owners;201/101/107/306; independent original source/DB receipts | Reliability release FAIL; approved safe coding can continue |
| CHK002 checkpoint/rollback | prior checkpoint/operator decisions, draft writer compatibility report | Runtime/DB owners102/132/306; preserve0040/0041 refusal and raw state | Unsafe collector/old-writer rollback remains blocked |
| Global performance / duplicate telemetry | main GLOBAL_UAT_REGISTER RM036/037; previous prefetch batching is partial | Platform/API owners135/107; task-owned controlled reproduction; no causal claim from old operator observation alone | P0 provisional global acceptance gap; do not drop telemetry to improve latency |
| Central collector administration | main RM039 approved architecture, implementation OPEN | Resource/runtime owners136; same IDs/revisions/deployment history | One-time onboarding must not become competing permanent configuration owner |
| Current main publication failure | MAIN_CI_SNAPSHOT publish exit1 before any build; no detailed log returned | Release owner503; approved PR/main authorization inputs; no rerun/bypass | CI/release evidence blocker, not a diagnosed application regression |
| Independent vulnerability/license/image clearance | main SECURITY_GATE_POLICY and retained baseline/remediation evidence; Issue68 open | Security/legal/owner123/303; exact image identities/SBOM/NOTICE/reviewer | SECURITY BLOCKED; green dependency checks not clearance |
| Native authority and qualified receipts | PR80 OC007/008; zero qualified proof/receipt in controlled fixtures | Explicit read-only target/build/native chain, issuer/reviewer/TLS/network/credentials301 | Genuine confirmation/admission/live cutover not certified |
| Settings/account fields | merged closure OWNER_DECISIONS | Product/security202; exact keys/ranges/roles/reauth/audit/secret references | SET02 implementation waits contract, not arbitrary config editor |
| Workflow calendar/threshold/event catalog | PR80 decision register D07/D08, conflict CF07 | Product/architecture204/207; exact examples and original source | No invented recurrence, threshold, severity or override semantics |
| Retired channels | worker.notifications.dispatch; CF04 | Product205; explicit channel disposition | PagerDuty/ServiceNow not supported; generic webhook is not their adapter |
| Entitlement design | PR80 Journey33 bounded principles and LIC001–008 | Product/licensing203; exact edition/signature/offline/grace/permissions/gates | No license-specific implementation/test clearance; do not invent LIC029–050 |
| Source authority |134-row canonical index, source-recovery records | Owner208:62 original IMP definitions,17 active OC proposals,30 numbered journeys | Missing definition is not a missing approved feature to implement |
| UAT register namespace collision | GLOBAL_UAT_REGISTER UI numbers differ from approved UI_001_023_REGISTER wording | Owner source-qualified mapping208; retain both originals | Never overwrite canonical UI IDs or silently add duplicates |
| Private target / DR / operational configuration | OPS_DEPLOY_001 | Network/runtime/security/DB owners304/305; approved topology/CA/proxy, capacity, recovery | No target, production/UAT access, deployment or RPO/RTO certification here |

## Historical defects and issue disposition

[39 original RM records](HISTORICAL_DEFECT_DISPOSITION.csv), [open GitHub issue metadata](OPEN_ISSUES_SNAPSHOT.json). Open historical issue titles (e.g. enum migration, absent tests/adapters, hard-coded UI, collector ownership) are not automatically current reproduced bugs: code/tests have since changed. No issue is closed or created by this audit. RM036 remains global P0-provisional;037/038 are P1-provisional;039 approved architecture/open implementation. UI labels in the UAT register require source-qualified references; they do not redefine canonical UI-007 or other approved IDs.

## Deferred work and approvals

301–306 are external qualification;401/402 formal UAT. They have explicit separate task types and UNESTIMATED external availability, not fake calendar commitments. No contact with providers/maintainers, live discovery or real credentials. No customer database migration. No security waiver, PR merge, deployment, Stage3 authorization or OC-DEV-002 implementation. This report is for owner review only.

