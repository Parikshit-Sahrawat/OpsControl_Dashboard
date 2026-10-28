# Open risks — removal incomplete

1. Full backend discovery has two import errors; security-bearing cluster tests must be replaced with unavailable-route/immutable-history/tenant-preservation assertions, not silently deleted.
2. 217 skipped tests and unexecuted PostgreSQL/HTTP/provider regressions block acceptance.
3. Legacy tables/models and isolation fences deliberately retained; destructive retirement blocked until consistent export/restore and attribution review.
4. Broad input/configuration paths, obsolete test fixtures, legacy rendering branches, safe-evidence fields, current guides and generic deployment matches require complete semantic reconciliation. No claim of repository-wide removal completion.
5. No live provider or UAT validation, no hosted CI clearance, no release promotion.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO
