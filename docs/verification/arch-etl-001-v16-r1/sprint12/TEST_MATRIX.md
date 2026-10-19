# Bounded shared-resource authorization test matrix

Fixture: [test_sprint12_shared_trust.py](../../../../backend/tests/test_sprint12_shared_trust.py), run with the owned disposable PostgreSQL harness; [verification](VERIFICATION.md). Actors are provider AB (grants A and B), A-only and none. The fixture seeds **two separate customer-owned VMs** solely to test existing denials. It cannot turn those into the target one shared canonical VM; this distinction is material.

| # | Required scenario | Actual Sprint 12 observation | Status |
|---|---|---|---|
| 1 | Both authorized views reference the **same canonical VM** | Existing `MonitoringResource.organization_id`, unique `vm_id`, and scoped dependencies prohibit second customer association. Second B binding to A VM rejected by DB guard. | **BLOCKED_BY_CURRENT_MODEL**; not a positive pass |
| 2 | Unauthorized customer cannot discover VM through inventory/detail | A-only ORM and direct inventory handler return A resource only; direct resource/detail handlers return 404 for B resource; none sees zero rows. | **PASS** for controlled direct handlers/ORM; no new HTTP transport run |
| 3 | A-only cannot read B-only application telemetry | A-only scoped `Application` query returns A app, not B app. No B telemetry payload read attempted in this fixture. | **PARTIAL**: identity isolation observed; telemetry case NOT RUN |
| 4 | Shared VM telemetry only via approved associations | Shared association/projection does not exist; cannot attest field subset/provenance. | **BLOCKED_BY_CURRENT_MODEL** |
| 5 | Forged customer/resource/relationship IDs denied | Forged B selection gives empty `choose`; B resource direct detail 404; B→A dependency insert rejected by composite FK. Exact relationship-ID HTTP read and cursor forgery not run here. | **PARTIAL**: tested cases pass; remaining HTTP cases NOT RUN |
| 6 | Invalid/ambiguous source attribution rejected/quarantined | Unknown or contradictory method IDs raise 422; approved method ID accepted. Missing method ID remains allowed by explicit legacy path. No shared attribution quarantine exists. | **PARTIAL**; no shared-source quarantine claim |
| 7 | Collector credentials cannot broaden customer authority | Collector/source/org checks inspected in [telemetry API](../../../../backend/app/telemetry/api.py); no new credential-submission HTTP test in this sprint. | **NOT RUN** as end-to-end credential test |
| 8 | Customer selection is not a grant | A-only forged B selection yields empty; none gets no resources even if A+B selected. Existing Sprint 08 no-selection/deny tests passed in same run. | **PASS** in controlled fixture |
| 9 | Derived graph/incident does not leak customer identity | Same-customer dependency FK rejects B→A edge; customer-scoped incident code inspected. Shared projection/aggregate cannot be tested until designed. | **PARTIAL**; shared-derived case blocked/unverified |
| 10 | Method-specific owner and fence remain | Existing cross-customer method-FK and live-lease fence PostgreSQL tests passed in same owned run. | **PASS** for those existing assertions |

No weakening of FK, resource owner, source generation, customer grant or denial semantics was performed. No real agent certificate, target firewall, external notification or genuine Pentaho RT-001–RT-020 test was run. These fixture results validate existing negative controls, not GOV-04 completion or production acceptance.
