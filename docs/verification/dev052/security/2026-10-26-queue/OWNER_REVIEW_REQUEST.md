# Accountable engineering decision requested — 2026-10-26

**No approval recorded. CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED;
RELEASE NO-GO.** This request is review material, not permission to operate.

Runtime/collector engineering, operations and release owners must decide how to
address the measured full-queue restart defect. No custom binary, upstream fork,
production version transition or real-target replay is authorized by this work.

| Decision | Evidence for review | Accountable reviewer / disposition |
|---|---|---|
| Native queue repair path | 0.123.0 deletes ten in-flight payloads then rejects replacement at capacity. Newer recovery avoids that rejection but partial-requeue SIGKILL loses nine. Review an atomic replacement transaction or resumable existing-index design with upstream maintainers. | Runtime engineering owner — REQUIRED / unassigned |
| Custom binary/fork, if chosen | Pin upstream source, narrow patch, toolchain and binary/image checksums; review metadata compatibility, capacity accounting, retries and every transaction cut before execution/promotion. No custom binary was built here. | Runtime and supply-chain owners — BLOCKED, approval absent |
| Supported version transition | Ordinary .163.2-labelled binary restart pass is insufficient; crash probe fails, matching public source-tag provenance is incomplete, and CHK-002 protobuf rollback remains blocked. Keep 0.123.0 guard. | Runtime/release owners — BLOCKED |
| Finite source-replay candidate | Review `replay.py` and runbook; exact legacy SHA, JSON schema and reserved marker, 10,000 IDs/16MiB bounds, source retention/completeness, trusted independent PG snapshots and stopped-writer assumptions. Initial fingerprint-collision failure and corrected finite recovery are both preserved. | Operations/runtime owners — REVIEW REQUIRED, not approved for real use |
| Duplicate/order consequences | Distinct IDs alone do not prove no duplicates. Examine API accepted attempts, PG physical rows and phase reconstruction. Stale snapshots/new transactions can cause duplicates; no exactly-once or ordering guarantee. | Application/data owners — REVIEW REQUIRED |
| Missing/expired/corrupt state | Missing archive coverage or expired retention stops replay. Corrupt queues and storage faults are not repaired by this utility. Preserve evidence; no reset/delete-to-pass procedure. | Operations owner — RECOVERY DESIGN BLOCKED |
| Production integration and loss detection | No automatic source inventory, receipt export, reconciliation alert or replay hook is shipped. Test-ledger detection is not production detection/delivery. Define operational integration, retention budgets and acceptance boundary first. | Runtime/operations owners — BLOCKED |

Reviewers should record name, role, reviewed commit and artifact hashes, accepted
support boundary, decision/date and follow-up issue. A missing signoff is not an
exception or waiver. No unrelated CVE/pip/legal/final-image/CI disposition changes.
