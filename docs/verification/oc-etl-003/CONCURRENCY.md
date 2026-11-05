# Concurrency and security acceptance

Implementation boundary: authenticated dependency-create POST, current immutable job/workflow association rules, PostgreSQL READ COMMITTED. Each graph write holds a shared authorization lock and an exclusive lock on its own authorized workflow until commit/rollback. Access/session mutations retain the original exclusive authorization lock. No new global serialization is introduced.

| Actual test | Required observed result |
|---|---|
| Opposite edges A→B / B→A | HTTP 201 + 409; one edge; persisted graph acyclic |
| Long graph A→B, C→D plus concurrent B→C / D→A | 201 + 409; three edges; complete graph acyclic |
| Nonconflicting A→B / A→C | 201 + 201; two edges |
| Same edge twice | 201 + 409 duplicate; one edge; subsequent different write succeeds |
| Blocked workflow A while workflow B writes | B commits while A waits; A commits after release |
| Workflow row held beyond five seconds | HTTP 409 busy; no partial edge; retry succeeds |
| Exclusive authorization mutation lock | Dependency request waits on shared advisory lock; no edge until release |

All seven passed in final/regressions.log. Four graph races independently query persisted edges and assert acyclicity; their JSON captures PostgreSQL lock-wait session IDs and HTTP outcomes. Synchronization uses real database row/advisory locks and pg_stat_activity, not mocked transaction/auth boundaries. Existing authenticated HTTP tests additionally exercise role denial, cross-tenant/workflow references, self-dependency, creates, updates, hidden resources and authorization boundaries. Existing scope-hook tests preserve immutable relationships. No dependency-update endpoint or mutable graph endpoint was introduced.

The old shared exclusive authorization lock already serialized ordinary HTTP writers. Consequently, prior unsynchronized graph validation was a structural risk, not a newly reproduced HTTP exploit. The failed first concurrent attempt is retained in run2 and led to the narrowly scoped shared-lock change. Direct privileged SQL and future writers must independently honor the graph-lock contract; this is not a database trigger enforcing acyclicity against superusers.
