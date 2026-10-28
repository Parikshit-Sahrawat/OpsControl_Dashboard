# Accountable owner review request — pending, 2026-10-25

No signoff is inferred from authorization to investigate. **CHK-001 FAIL, CHK-002
BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.** This request is for review/future scoped
work, not permission to deploy, merge, waive findings or begin DEV-05.2B.

| Accountable role | Concrete decision requested | Evidence / outstanding requirement | State |
|---|---|---|---|
| Collector engineering owner | Review the minimal synchronous-handoff candidate at7af6927a16056597794c42549a813d3408860a57 | Two in-memory windows reproduced; syscall/API/DB probes pass; alpha upstream gate, one-record request rate and shared-log-pipeline effects need review | PENDING |
| Collector/release owner | Authorize a separate plan for the pinned0.123 full-queue recovery deletion | Default256 queue loses10/267 after staggered checkpoints; changing the pin/guard or custom binary is not authorized here; do not treat a larger queue as a fix | PENDING / BLOCKED |
| Operations owner | Define end-to-end retention/receipt audit and capacity limits | Permanent400 and retention expiry lose IDs; independent inventory detects test losses only; production detector, long outage and disk/power failures untested | PENDING / BLOCKED |
| Rollback owner | Resolve CHK-002 independently | No change to protobuf conversion, original recovery utility or approved transition state | BLOCKED |

A larger queue may reduce frequency but cannot prove loss-free crash recovery.
Replaying a retained source can mask queue deletion and introduces duplicates;
this work does not extend the recovery utility or claim exactly-once semantics.
Any future fix must rerun both burst and staggered independently reconciled cases,
preserve the observed failures, and satisfy the independent security gates.
