# Open decisions and accountable ownership

**Documentation readiness only; no implementation or execution authorization.**
The existing [governance comment](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/68#issuecomment-6414180530)
approved Parikshit as runtime engineering and independent verification owner for
the bounded isolated feasibility study. H recognizes those named roles, but its
explicit documentation-only boundary does not authorize tests, builds, transitions
or upstream messages. Documentation checks are not an independent human signoff.

| Decision / role | Evidence or outstanding prerequisite | State |
|---|---|---|
| Upstream response, exporterhelper owners `bogdandrutu`/`dmitryax` and Collector approvers | Issue16236 has no comments or assigned reviewer at observation; codeowner identity is not commitment | **PENDING** guidance/ownership/support, not refusal or acceptance |
| Supported corrected source/distribution, upstream maintainers/release owners | Exact invariant-preserving source commit, distribution dependency binding, supported backend/schema, artifact digest and support window | **BLOCKED**, no qualifying correction established; v0.164.0 queue unchanged |
| Storage contract, storage owners `swiatekm`/`VihasMakwana` with relevant approvers | Atomicity/resumability, admission/commit/fsync guarantees, error outcomes, migration/downgrade support | **PENDING**, no assigned review or accepted design |
| Local candidate/cut design, runtime engineering owner Parikshit for isolated study | Exact source/binary/config, witness mechanism, non-root/isolation limits, original267 workload and no replay masking | **PENDING review**; H may document but cannot implement |
| Later N1–N4 execution, user and verification owner Parikshit for isolated study | Separate scoped authorization; supported candidate; ten repetitions per cut, repeated crashes/restarts, receipt oracle, exact numeric budgets | **BLOCKED / NOT RUN in H**; earlier research approval does not override H's restriction |
| Receipt/duplicate contract, API/data-persistence owner (name pending) | Commit-before-success, consistent independent PG snapshot, all attempts/rows/IDs, approved ACK-ambiguity duplicate/order budget | **PENDING**, no backend changes or invented signoff |
| Operational fault/retention boundary, SRE owner (name pending) | Source completeness/retention, observer liveness, failure escalation, snapshot permissions and full-state rollback, power-loss scope | **PENDING**; production replay contract not implemented/approved |
| Queue rollback vs filelog CHK-002, runtime/operations/verification owners | Independent populated old/new queue and checkpoint proof, interrupted migration, restore/post-backup admissions and physical duplicates | **BLOCKED**, one gate cannot clear the other |
| Security/supply chain/release, accountable security and release owners (names pending) | Independent vulnerability, licensing, approved image, provider and operational gates | **SECURITY BLOCKED / RELEASE NO-GO**, unchanged |

Any future approval must identify person/role, exact reviewed commit and digests,
scope, date, conditions and disposition. No author claim, issue creation, bot
reference, review activity, release-note link, or silence substitutes for it.

## Next narrow action

Continue read-only response tracking when requested. The upstream issue already
exists, so submitting the G draft again is not recommended. Its stale "not
submitted" text could be corrected by its authorized owner; this task grants no
permission to edit it or contact maintainers. A later refresh should retain new
comments/linked PRs/releases and classify the precise statement before changing
readiness. No polling service or continuous monitor was installed.

If upstream supplies a supported candidate, return source/artifact/support and
boundary evidence for a separate scoped qualification decision. If only an
unmerged patch/custom fork is offered, do not build or apply it without explicit
source/maintenance/build authorization. If support is declined or unavailable,
return to the [existing ADR](../2026-10-26-adr/ADR-CHK-001.md) for accountable choice
between maintained native correction and enforceable production bounded replay.
Neither alternative is approved by this readiness package.

No waiting period counts as an answer, no release criterion is weakened, and
PR69 stays draft. **CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
