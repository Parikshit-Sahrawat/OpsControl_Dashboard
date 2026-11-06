# Readiness transition matrix

Backend: `app.etl_bindings.service.readiness`; endpoints GET `/api/v1/etl/workflows/{id}/readiness` and the additive `readiness_dimensions` key in `/monitoring`. No save starts a source or a workload. Existing legacy readiness fields remain for compatibility and continue to state BLOCKED/UNVERIFIED.

Envelope: schema_version1, explicit server evaluated_at, freshness policy `ETL_SOURCE_RECEIPT_V1`, Job/binding IDs and six independent dimensions. Policy uses the already existing resource-context threshold max(120, interval_seconds×3); all selected methods constrain the threshold (minimum), so adding a slow method cannot make stale evidence current. Both observed and server-committed receipt clocks must satisfy it; future clocks are CLOCK_UNCERTAIN. Unknown/unattributed/legacy/quarantined records never become current binding receipts. This does not change existing `_item` or source_readiness thresholds.

| Trigger | Configuration | Binding | Activation | Connectivity | Freshness | Operational health |
|---|---|---|---|---|---|---|
| Job saved, no binding/evidence | Supported runtime VALID or INCOMPLETE, scoped explicitly | MISSING | BLOCKED | UNVERIFIED | MISSING | UNVERIFIED |
| Explicit Stage | Unchanged | STAGED; authority UNVERIFIED | BLOCKED | Existing current runtime proof only; otherwise UNVERIFIED | MISSING without a qualified binding receipt | UNVERIFIED |
| Same-target staged reader replacement | Unchanged | New STAGED version, old version end-dated | BLOCKED | Re-evaluated | No inferred continuity | UNVERIFIED |
| Source generation/reader changes | Unchanged | STALE | BLOCKED | Unverified if stale | No current binding receipt | UNVERIFIED |
| Normal source lease fence advances | Unchanged | No identity transition; existing ticket fence still checked | BLOCKED | Re-evaluated | No inference | UNVERIFIED |
| Retire | Unchanged | RETIRED; immutable history retained | BLOCKED | Physical source fact remains separate | MISSING for effective binding | UNVERIFIED |
| Self-confirm | No mutation | 403, unchanged | BLOCKED | Unchanged | Unchanged | UNVERIFIED |
| Distinct reviewer without authenticated proof | No mutation | 409, unchanged | BLOCKED | UNVERIFIED | MISSING | UNVERIFIED |
| Current reader proof without native authority attestation | No mutation | D09 confirmation BLOCKED | BLOCKED | Current reader proof can be reported separately | No qualified binding receipt | UNVERIFIED |
| Fresh/stale/future-clock policy probes | No configuration mutation | No provider qualification | BLOCKED | Not certified | Pure policy function FRESH/STALE/CLOCK_UNCERTAIN at exact boundary; tests do not synthesize qualified routing | Never HEALTHY from a probe |

There is no new Workflow activation action or successful CONFIRMED transition in this increment. Positive qualified confirmation, aggregate ACTIVE, genuine provider connectivity, authoritative native operational health and live reader cutover are BLOCKED/NOT TESTED. D03's complete positive activation contract remains incomplete despite owner design/implementation approval; D09 evidence and a reviewed authority mapping remain prerequisites. Do not mark these cases PASS based on negative gate tests. D07/D08 event/calendar/threshold semantics are not invented.
