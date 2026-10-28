# ADR CHK-001 — native queue correction or enforceable bounded replay

**Status: Proposed / Pending accountable approval**

Date: 2026-10-26 (Asia/Calcutta)

Tracking: [Issue #68](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/68),
[draft PR #69](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/pull/69)

Evidence/repository baseline: `a4886b894aaeb2aa2ed48d3abe1748afe41a05fa`

**CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**

D tested product commit `97be9b3d1acffc83367b79cdc9ee179f8b694c05`; its bounded
replay implementation is `d48cf540aa1759b770eee6e30d619f939c281f0a`. The original
product baseline is `f617cc653a965c2ad1bb7edf9e20237e40044b97`. This ADR adds no
implementation or new test execution to those source bindings.

This ADR proposes an architectural decision and acceptance criteria. It authorizes
no implementation, custom binary, version transition or production operation. The
0.123.0 production pin/guards, queue code, checkpoint recovery utility and unrelated
security workstreams remain unchanged. No runtime tests were rerun for this ADR.

## Decision rule and recommendation

Apply the user-approved rule as three separate requirements:

1. **Prefer A, supported native correction, only after safe saturated and
   interrupted recovery is demonstrated** against the exact candidate and its
   declared support boundary. An ordinary restart or newer version number is not
   sufficient. Independent reconciliation remains defense in depth under A.
2. **B, production bounded replay, may be primary only if source completeness,
   retention and missing-ID detection are enforceable in production.** Native
   failure does not automatically qualify B. The current offline helper and lab
   ledger do not enforce those production obligations.
3. Neither option is currently eligible. Keep the failure/blocking gates and
   obtain accountable approval of the support boundary and implementation scope.
   Passing either reliability gate would not independently clear security,
   licensing, provider, release-image or other release gates.

Recommend an **owner-gated native correction feasibility slice** as the next
narrow task, specified below. This is a preference for what to investigate next,
not acceptance of a native fix that does not yet exist. Keep bounded replay as a
conditional recovery design and independent reconciliation as mandatory for both.
If no supported native candidate can meet the criteria, return to this ADR; permit
B as primary only after every enforceability gate in its contract is satisfied.
If neither qualifies, maintain NO-GO rather than accepting undetected loss.

## Verified historical observations

These are observations from preserved experiments, not new DEV-05.2A.3E runs.
[Evidence index](EVIDENCE_REFERENCES.json) binds the source commit, paths, selectors
and SHA-256s. Counts are run-local; repeated IDs across labs are different sets.
The [D decision](../2026-10-26-queue/QUEUE_DECISION.md) and
[root-cause proof](../2026-10-26-queue/ROOT_CAUSE.md) provide context.

| Observation | Actual result and scope | Primary evidence |
|---|---|---|
| Guarded 0.123.0, unchanged generated 256-request queue, ten consumers, staggered checkpointed writes | **267 expected / 257 persisted / 10 missing**, 257 accepted record attempts, 257 physical rows, zero duplicates. Missing `event-0000`–`event-0009`. | D `guarded-baseline/reconciliation.json`, `e2e.json`, queue snapshots and runtime log |
| Experimental newer binary, ordinary saturated restart | **267/267**, zero physical duplicates; necessary but insufficient | D `replay-attempt1/reconciliation.json`, `replacement_full` |
| Newer binary, interrupted partial re-enqueue | **258/267, nine missing**, twice. After all replacement commits, two other cuts delivered 267/267. | D `boundaries-attempt1` and `boundaries-repeat` partial cases; `faults-attempt1` completed-re-enqueue repeat |
| Three bounded replay recoveries | Saturation, repeated crashes and ENOSPC-then-restart each advanced **257 → 267/267**, 267 accepted attempts / 267 rows / zero duplicates; two later restarts preserved counts. | D `replay-marker/phase-reconciliation.json`, `faults-attempt1/phase-reconciliation.json`, independent DB rows/receipts |
| Earlier replay attempt | **257/267 after replay**, FAIL: matching leading bytes caused filelog fingerprint collision. The later marker fixed that finite case. | D `replay-attempt1/phase-reconciliation.json` and raw replay/state archive |
| Retention expiry | Ten IDs remain missing; replay **BLOCKED** | D `replay-marker`, `retention_expiry` |
| Corrupt queue metadata | Startup `invalid database`; **0/267** persisted; recovery **BLOCKED**, hashed original retained | D `faults-attempt1`, `corrupt` |
| Permanent HTTP400 rejection | **0/4** before and after replay, **FAIL** | D `faults-attempt1`, `permanent_rejection` |
| API outage and retry | **4/4**, four accepted attempts / four rows / zero duplicates | D `faults-attempt1`, `api_outage` |
| D selected native matrix | **4 PASS / 13 FAIL**; all 18 attempts **4 PASS / 14 FAIL**. Successful recovery never relabels the native phase. | D `test-matrix.json`, `all-attempts.json` |
| D regressions | **91 PASS, 0 FAIL, 0 SKIP**: 17 replay + 17 unchanged checkpoint/security + 57 collector/Agent/auth/worker | D `unit-marker.log`, `checkpoint-regressions.log`, `collector-security-regressions.log` |
| Previous durability and checkpoint work | C selected matrix **20 PASS / 6 FAIL**; a burst case delivered 271/271 with **255 duplicate rows**. B interrupted upgrade lost **16 of 44**; bounded restore/replay recovered 44 distinct in **100 rows, 56 duplicates**. | [C matrix](../2026-10-25-durability/test-matrix.json), [B matrix](../2026-10-25-checkpoints/test-matrix.json) and B phase DB reconciliation |

The D native phases total 4,013 expected / 3,634 persisted / 379 missing; after
three recoveries, final cuts total 3,664 persisted / 349 missing. These include
intentional negatives and repeated experiments; they are not production loss rates.

**Causal observation:** old recovery reads in-flight payloads, commits their bulk
deletion, then separately re-enqueues each. A full queue rejects replacement in
0.123.0. Removing that check avoids the capacity rejection but not a crash between
deletion and replacement. Source checkpoint advancement, queue persistence, API
commit and transport ACK are distinct facts. A burst reread can mask the queue
loss; therefore source-replay-disabled native tests are necessary.

**Evidence limits / assumptions:** the experiments used synthetic bounded IDs,
local storage, actual authenticated TLS API transactions and isolated PostgreSQL;
they are not genuine-provider or production-load certification. D's first two new
instrumentation runs did not freeze exact in-memory fixture-source hashes; later
repeated probes did. SIGKILL/fsync evidence does not establish power-loss safety.
No shipped complete source inventory, autonomous production gap detector, archive
retention enforcement or trusted receipt-export contract has been demonstrated.
Production throughput, retention budgets, duplicate tolerance and recovery SLOs
are outstanding decisions, not values inferred from successful small fixtures.

## Alternatives and decision matrix

| Criterion | A — supported native persistent-queue correction | B — production bounded replay contract |
|---|---|---|
| Core invariant | Every admitted unacknowledged item remains durably recoverable through all recovery transactions; success cannot follow failed durable admission | Every admitted source event has a complete independently durable inventory/payload until independently verified delivery; gaps trigger bounded recovery |
| Mechanism to evaluate | Preserve old payload until replacement + metadata commit atomically, or resumably dispatch existing durable indices. Exact supported upstream behavior must be reviewed. | Durable source capture, retained sealed windows, independent scoped receipts, continuous gap detection and controlled idempotent replay |
| Current evidence | Guarded native FAIL; tested newer partial-requeue FAIL. No fully qualifying supported correction identified in D's frozen research. | Three finite recovery PASS cases; expired source, corrupt startup and permanent rejection remain failures/blockers |
| Safety on full queue | Must prove recovery does not reject/drop existing durable work or deadlock; increasing capacity alone is inadequate | Requires enforceable producer admission/backpressure and retained archive when collector queue fails |
| Crash and storage boundary | Native transaction and filesystem proofs; committed old/new state always recoverable; arbitrary corruption cannot be assumed recoverable | Capture/inventory/receipt/replay journal boundaries and independent archive failure domain; cannot restart an invalid queue by itself |
| Duplication and receipts | ACK ambiguity can resend; independently reconcile accepted attempts and physical rows | Same-plan publication can be idempotent, but stale/new plans may duplicate; downstream semantics require approval |
| Operational cost | Smaller production operational surface if maintained upstream; still needs gap detection, receipts and rollback validation | Adds production capture, storage/retention, detector, authorization, reconciliation, recovery ownership and escalation services |
| Compatibility / CHK-002 | Exact binary/source, generated config, all five methods and both queue/filelog state rollback must qualify | Legacy helper requires exact 0.123.0 SHA; replay neither converts protobuf checkpoints nor repairs a corrupt queue |
| Promotion prerequisite | All native acceptance cases within approved failure model pass, provenance/support/rollback reviewed, explicit transition approval | Every production contract clause enforceable and tested, numeric budgets and operating ownership signed; native failure must remain visible |
| Present decision | **Not eligible; preferred next investigation only** | **Not eligible as primary; finite experimental recovery only** |

There is no numerical scoring that can trade missing data for convenience. Both
options must retain independent reconciliation; counts derived solely from queue
contents or successful API responses cannot enumerate records lost upstream.
A custom patch/backport is not a third accepted option or automatically
"supported": it enters A only with explicit accountable maintenance, source/build
review, binary provenance and execution/transition approvals.

## Binary support, provenance, compatibility and rollback

| Identity | Verified historical identity | Decision relevance |
|---|---|---|
| Guarded Linux amd64 0.123.0 | Binary SHA-256 `6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213` | Current product contract, not a reliability/security clearance; unchanged |
| Experimental binary reporting 0.163.2 | Binary SHA-256 `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb` | Exact tested bytes; not an approved replacement |
| Recorded candidate image | `otel/opentelemetry-collector-contrib:0.163.2@sha256:7f22d2a6748110ffb6a59bc0df448bccbf501cdb667d610ede4c61d3863d5849`; amd64 config `sha256:a64fa52ad3b55378bb62d8642439aaf0ec3abf45a8ddc1ac02bac31eea7a6565` | Image identity is not final product release approval or source attestation |

[A.3 compatibility evidence](../2026-10-25-collector/COLLECTOR_DECISION.md) records
an experimental five-method authenticated lab and a legacy-write-mode overlay.
The distribution manifest/labels recorded a .163.2 release with .163.0 Contrib
components. D's public Contrib .163.2 source-tag lookup failed; its frozen latest
release response was .163.0. Resolve the authoritative distribution-to-component
source mapping and supported maintenance channel before accepting a binary. These
facts neither prove tampering nor permit assuming source equivalence.

Upstream PR13330 (`e2954b98139a839d31cd7ae4d826966f33a9180f`) removes the recovery
capacity check; frozen tag ancestry puts it in core v0.130.0, not v0.129.0. Neither
version was binary-certified by those ancestry checks. D's inspected main commit
`82148555675e5a0a201189cd4220395eb8baa1ad` retains delete-before-replacement. This
ADR performs no new upstream search and does not assert that no later fix exists.

Any A candidate must bind official source/distribution, patch set if any, build
inputs, architecture, immutable image/binary SHA, generated config hash and state
schema; complete [native plan](NATIVE_ACCEPTANCE_PLAN.md) and the existing five-method,
TLS/auth/egress/supervisor contracts. A custom binary bearing the same version
string must not silently replace the pinned hash. Approval to test is distinct
from approval to ship or transition a guard.

**CHK-002 remains independent and BLOCKED.** Default newer protobuf filelog
checkpoints caused legacy downgrade startup failure (`decoding file count`). The
A.3 experimental legacy JSON write mode passed a finite rollback; B's stopped
backup/restore + replay was bounded and produced duplicates. Neither is a general
protobuf conversion or coordinated production rollback. Queue metadata also
changes independently of filelog encoding. Require preserved full-state backups,
hashes/config identity, populated old/new queue and filelog state, interrupted
upgrade/rollback and receipt reconciliation before any transition. If safe rollback
is not demonstrated, promotion is BLOCKED; no destructive reset or unapproved
one-way migration is an alternative. Do not change the CHK-002 utility here.

## Accountable approvals and outstanding decisions

The user approved the decision rule, **not** these designs, support budgets,
custom binaries or production transitions. Names are not available: role owners
must nominate accountable individuals. Every row below is **PENDING; no signoff**.
A future record must identify person, role, exact reviewed commit/digests, support
boundary, decision, date and conditions. No silent or inferred approval.

| Named role | Required decision |
|---|---|
| Collector/runtime engineering owner | A's recovery invariant, supported candidate or upstream engagement; review patch/maintenance obligations if custom; approve exact transaction probes |
| Source/ingestion engineering owner | B's atomic durable capture, complete stable-ID inventory and enforceable producer admission; identify unsupported sources |
| API/data persistence owner | Independent tenant-scoped receipt semantics, commit durability, consistency/watermarks, duplicate and ordering effects |
| SRE/operations owner | Storage failure model, retention/capacity/backpressure budgets, detector liveness, paging, restore/escalation procedures and recovery SLO |
| Independent verification owner | Witnessed failure cuts, adversarial gaps/duplicates, negative cases, source/binary bindings and acceptance evidence completeness |
| Security/supply-chain owner | Binary/source trust, custom build authorization, receipt/archive access and secret protections; existing independent security blockers remain |
| Release/change owner | Accountable role assignments, accepted ADR, separate test authorization and eventual coordinated transition/rollback approval; no release GO here |

If operations cannot guarantee source retention or an independent complete
inventory, B is rejected as primary for that source class. If native correction
cannot demonstrate safe saturated/interrupted recovery, A cannot be accepted.
These are exclusion conditions, not requests for vulnerability or data-loss waivers.

## Recommended next narrow task — proposal only

**CHK-001 native recovery feasibility slice (proposed DEV-05.2A.3F).** After runtime
and verification owners approve the scope, identify one authoritative maintained
upstream correction for the destructive recovery window and document its exact
source/digest and old/new metadata invariant. If none is available, deliver an
upstream design/patch proposal for review; do not build/run an unapproved fork.

For one approved candidate only, extend an isolated queue transaction fixture to
observe old-key deletion, replacement metadata/payload commits and restart. Reuse
the unchanged 267-ID staggered baseline, with source replay disabled in native
acceptance. Execute N1–N4 of the [plan](NATIVE_ACCEPTANCE_PLAN.md), binding results
to exact sources/binary and independently persisted receipts. Include ten repeats
per cut, partial migration and repeated restart. Stop with FAIL on any actual gap;
BLOCKED if the required candidate provenance, approval or observation point is
unavailable. Report evidence before proposing any production integration.

Exit deliverable: one reviewed invariant/source comparison and reproducible narrow
fixture evidence, or a precise unsupported-candidate blocker. Even if N1–N4 pass,
N5–N8, the five-method contract, rollback and independent gates remain pending.
No product guard/config/utility change, production replay service, unrelated
security remediation, release-image publication, deployment, merge or DEV-05.2B
is included. A separate future task/approval is required for B's enforceable
production capture/retention/detection implementation if native qualification fails.
