# CI-003B isolated product scope correction

Base origin/main ffe5ac285ab8aef33a1139bce6f3da79be3d6d33. Remove only incident-management UI navigation/mounts/ETL tabs and two UI modules; backend alert/correlation/history, migrations and RBAC untouched. Legacy page preference is denied by canNavigate; retired ETL hashes fall back to inventory. No integration into PR84/85.

Real PostgreSQL17/API/React/Playwright harness exit0; original unchanged ci_scope_acceptance.mjs now PASS. Additional browser direct route checks for #/incidents, #/operations/incidents and #/pipelines/incidents PASS. Existing authenticated HTTP23 groups, authorization browser5 groups and eight-step browser workflow pass. Raw98-test PostgreSQL results and cleanup in integration/. Frontend lint/build and tests, background incident unit results attached. No genuine-provider or owner acceptance claim. Source worktree hashes bind the tested edits; implementation commit identified in handoff.

Test-only standalone harness derived from PR85 v16 acceptance runner retains scoped failure cleanup; backup hook unused. No collector change, merge, deployment or publication. Sprint1 NOT COMPLETE; CHK001 FAIL, CHK002 BLOCKED, SECURITY BLOCKED, RELEASE NO-GO.
