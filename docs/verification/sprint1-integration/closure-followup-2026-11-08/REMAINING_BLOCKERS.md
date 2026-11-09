# Remaining blockers and proven boundaries

| ID | Disposition | Exact remaining work / prerequisite |
|---|---|---|
|P0 resource context|IMPLEMENTED_VERIFIED within tested single-source boundary|Real PostgreSQL/auth HTTP covers primary Compute Instance/source atomicity, both legacy adapters, stale conflicts, OS incompatibility refusal and retained history. Coordinated environment propagation into a revisioned child API source still fails closed409; multi-source expected revisions and UI review remain PARTIAL.|
|P0 command interruption/revocation|IMPLEMENTED_VERIFIED at documented cuts|Actual authorization-lock revocation race, database connection death, API SIGKILL before ledger persistence, restart/retry and post-commit replay reconcile zero/one rows. No claim of all interruption cuts or power-loss durability. Collector application provenance is separate; no automatic application.|
|History/diff/detach/conflict UX|IMPLEMENTED_VERIFIED controlled browser scope|Pagination/detail/diff, explicit detach/restore, staged preview and conflict refresh preserve input and history. Draft is browser memory only; durable draft semantics/storage are not certified. Owner acceptance pending.|
|Catalogue publication|PARTIAL / separate concurrency gap|Source CAS is not catalogue CAS. Preserve immutable versions; catalogue expected-version/client convergence still needs its bounded implementation.|
|Provider applicability|BLOCKED_DEPENDENCY|Host and HTTPS template contracts tested; exact approved ETL provider template mapping and genuine qualification remain unverified. No synthetic provider success becomes attestation.|
|All seven image roles|FAIL / fresh built candidates PENDING|Original1,890 matches retained. Candidate pins and OS updates prepared; unchanged OTel0.123.0 compiled findings, Debian vendor-wont-fix High findings, PostgreSQL gosu Go findings and accountable licence obligations remain unresolved. Adequate isolated Docker build storage/hosted exact-final-head artifacts required. No severity/threshold/waiver changes.|
|PostgreSQL distribution change|BLOCKED for operational cutover|17-Alpine is an isolated candidate, not permission to point it at existing glibc volumes. Locale/collation, extension and real populated recovery compatibility must be certified before any separate deployment authorization.|
|Required checks|PRESERVED / admin transition BLOCKED|All13 unchanged. No removals. Authorized Administration-write credentials and proven exact check equivalents remain prerequisites for a future ruleset change.|
|Owner/independent review|PENDING|Owner desktop visual acceptance and independent PR approval required. No merge permission. Nine owner selections and formal UAT remain pending.|
|Independent release gates|UNCHANGED|CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO. D07/D08 remain pending. Sprint1 NOT COMPLETE; Sprint2 not started.|

Image/tool storage and proof limitations are evidence gaps, never artificial PASS. Review TEST_EXECUTIONS.json and raw failed attempts before claiming any wider completion.
