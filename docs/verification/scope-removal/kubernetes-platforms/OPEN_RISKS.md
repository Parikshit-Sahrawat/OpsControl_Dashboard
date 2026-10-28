# Remaining risks — closure review

1. Independent owner acceptance and final-commit hosted CI review remain required; PR 73 stays draft. CI status at the evidence commit is pending and its eventual result is recorded on the PR without creating a self-referential evidence-commit loop.
2. Two unchanged pinned OTel binary tests are SKIPPED/NOT TESTED. No collector version, guard, checkpoint utility or unrelated durability work changed. CHK-001 and CHK-002 remain unresolved.
3. Synthetic browser/API/configuration/provider fixtures do not certify genuine Windows/Linux/EC2/Pentaho deployments or independent UAT. Generic HTTP monitoring cannot classify the hosting substrate of every remote application.
4. PostgreSQL legacy tables, tenant fences and immutable decisions are retained. Future schema retirement requires an accountable owner, complete export/relationship inventory, retention approval, verified recovery and separate explicit authorization. No customer data was accessed.
5. Physical draining of an already-running remote worker process was NOT TESTED. Queued/leased cancellation, empty worker claim and rejection of stale lease results were executed; no claim of exactly-once delivery or durable queue correctness follows.
6. Environment storage is constrained. Final checks ran sequentially with task-owned tmpfs PostgreSQL and explicit cleanup; failures remain in evidence. Pre-fix exploratory release fixtures used anonymous volumes without publishing mount identities. One conclusively attributed failed-run volume was removed; older orphan-volume attribution is not established, so no broad prune was attempted. Final fixture identities/volumes and zero remaining containers are recorded.
7. Generic telemetry `namespace`, `pod`, `cluster`, `workload` and historical `k8s.*` labels remain intentionally. They do not register providers or grant tenant scope. Historical reports/architecture text are preserved under the prior scope supersession.
8. The remote scheduler now inspects persisted source/configuration for active or admitted remote work, including not-yet-due rows. Large-fleet throughput benchmarking was not part of this acceptance; correctness is verified in controlled fixtures.

All four requested closure workstreams now have passing scoped evidence; no known tested removal defect remains. This does not waive independent security, data retention, provider or release gates.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO**

9. The pre-existing auxiliary EKS ledger appends a literal backslash-n and is not valid JSON. Its original bytes are retained as `eks.json.raw.txt`; the new scope-http.json and full harness report.json are valid and carry the qualifying assertions. This ancillary serialization defect is disclosed, not treated as a passing JSON check.
