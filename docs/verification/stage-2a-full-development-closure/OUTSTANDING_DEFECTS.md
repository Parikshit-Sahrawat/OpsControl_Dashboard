# Outstanding defects and limits

- CHK-001 accepted telemetry loss remains FAIL; CHK-002 rollback compatibility remains BLOCKED. Existing failed DEV-05.2 evidence is unchanged.
- Security/image/license clearance remains BLOCKED. No waiver or genuine-provider certification.
- SET-02 has no approved editable-settings contract; SET-01 account security editing has no approved field/re-authentication/recovery contract. No arbitrary configuration editor or password policy was invented.
- Newly merged global UAT register retains RM-DEF-001–039 acceptance gaps, including Windows EXE delivery, agent-on dashboard latency, duplicate telemetry, journald permissions and one-time onboarding versus central collector administration. Its original observation/provenance is preserved; this task has no live UAT access. Source fixes in #74 are not blanket UAT closure. Independent symptom samples, representative load and authorized runtime remain prerequisites for those investigations.
- UI-005/UI-012 broad cross-screen consistency and newer eight-step journey acceptance are incomplete; historical ten-step screenshots cannot establish current completion. No status is silently upgraded on merge.
- The initial new browser found an Alerts accessible-name mismatch (fixed), then the V1.6 suite exposed 768px header overflow (fixed, rerun recorded separately). An initial new incident assertion confused permission-denial 403 with tenant-hiding 404 (test corrected to assert both independently, without changing backend security).
- Resumed release attempt hit ENOSPC; resumed V1.6 build hit a dependency relocation error introduced during environment repair. Both attempts remain failed evidence; retries are separate records.
- Prior `eks.json` probe emitted a literal unescaped newline. Bytes are retained as `.json.raw.txt`; no assertion/result was edited to conceal this serialization defect.

Full Stage 2A acceptance remains BLOCKED, not complete. This PR supplies bounded implementation and evidence, and explicitly identifies what it cannot accept.
