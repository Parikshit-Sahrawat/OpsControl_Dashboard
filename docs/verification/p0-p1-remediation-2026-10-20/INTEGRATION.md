# Direct main integration evidence

The owner authorized P0/P1 remediation, temporary-branch testing and normal main integration after mandatory gates. No separate PR was created. This is not deployment, production acceptance or authorization for a numbered future sprint.

| Item | Verified result |
| --- | --- |
| Audited/pre-integration remote main | `c694af45055557b062bedeb974d73140ac75c6c9` |
| Runtime implementation commit | `efabfb0f1d712d5b34ca2c018f29bf03bd8383f2` |
| CI-tested and integrated runtime main | `e7c31b7a54efa46f89b468f9df94c7928ef99a0d` |
| Quality, coverage, Docker CI | [39406560611](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39406560611) SUCCESS; verification19m47s and Windows source check SUCCESS |
| Pipeline/PostgreSQL CI | [39406563996](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39406563996) SUCCESS |
| Customer ownership/internal access CI | [39406567116](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/actions/runs/39406567116) SUCCESS |
| Local main integration | Separate clean worktree; old local main ancestor fast-forwarded to remote baseline, then reviewed remediation branch. No whole historical branch merge. |
| Post-integration validation |92 focused executions (86+6),8 actual PostgreSQL/HTTP remediation cases, metadata56 tables, frontend tests/lint/build PASS. |
| Remote push | Normal `git push origin main:main`, no force/admin/protection bypass; `git fetch origin main` and independent `git ls-remote` both verify exact SHA. |
| Remote source inspection |179 runtime blobs from fetched `origin/main` match the accepted SHA256 manifest; confirms corrections are actually on remote main. |
| PR33 | Head `9874944a593847ac26e6f758660c6dc71c47698b`, base main, open; no PR API write/merge/review/label operation. |
| Cleanliness/preservation | Main and temporary branch clean after their acceptance commits. Original worktrees/uncommitted audit/UAT evidence unchanged. Approved architecture/migrations/native fixtures unchanged. |

[Machine-readable verification](evidence/main-integration-verified.json), [CI jobs/steps](evidence/ci-accepted.json), [fast-forward log](evidence/main-fast-forward.log), [source manifest](evidence/runtime-source-sha256.json), [finding dispositions](DISPOSITIONS.md).

The final documentation-only follow-up carries this after-push evidence and corrects the focused-command module listing. It does not alter the accepted runtime, tests, workflows or migrations. The resulting containing commit's remote SHA is verified again after its normal push; a commit cannot embed its own hash. Its runtime is independently compared to the accepted179-file manifest. Any newly triggered duplicate CI run must be reported with its actual status, not presumed complete.

All confirmed P0 evidence defects and authorized confirmed P1 corrections are locally/CI proven. Shared-resource positive behavior, attribution policy, graph/aggregate/fence performance, real provider/CA/private routes, offsite/PITR and independently witnessed DR remain unresolved. [All16 readiness gaps](PRODUCTION_READINESS.md) and [conditional roadmap](ROADMAP_UPDATE.md) retain historical delivery credit. [Next bounded proposal](NEXT_SPRINT_PROPOSAL.md): independent affected-flow UAT and specifically approved shared-resource design; no automatic new implementation.

Pentaho **RT-001–RT-020: NOT RUN**. Native repeated child identity **UNVERIFIED**. Production **NOT READY**. No ETL workload, production/customer data change, source activation, deployment, force-push, branch deletion or PR33 modification occurred.
