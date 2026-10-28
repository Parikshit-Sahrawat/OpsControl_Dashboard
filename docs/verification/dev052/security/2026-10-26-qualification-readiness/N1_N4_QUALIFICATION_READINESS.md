# N1–N4 qualification readiness

**Definitions prepared; execution readiness BLOCKED; all four NOT RUN in H.**
This is an auditable checklist against the unchanged
[ADR acceptance plan](../2026-10-26-adr/NATIVE_ACCEPTANCE_PLAN.md), not authorization
to provision a lab or execute commands. [READINESS_STATUS.json](READINESS_STATUS.json)
records null new counts and per-case blockers. No unrun case has a runtime PASS.

## Reproducible setup and provenance prerequisites

| Requirement | Exact reference or required evidence | Current readiness |
|---|---|---|
| Pinned baseline | Production Contrib0.123.0; historical Linux amd64 binary SHA-256 `6bca4ddd928b4b0880f7ec6c16511922f740c497b4efa4b33915b2d54a729213`; pinned image `otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2` | Historical identities available; no new binary provision/verification or lab preflight in H |
| Corrected candidate | Authoritative maintainer statement, immutable source commit/tag, supported distribution/module mapping, architecture, downloaded binary/archive SHA-256 and image manifest/config digests; support and schema limits | **BLOCKED**: none qualifies. Core0.164.0 source is unchanged at the relevant queue boundary; no verified corrected binary/config identity |
| Component mapping | G binds distribution0.163.2 at `6c65793ec707f673304e52dfcb642684fda1a048` to core/Contrib0.163.0, including OTLP/HTTP→exporterhelper0.163.0 | Reference only, not a qualified candidate. Do not substitute distribution labels for dependency/source proof |
| Historical newer binary | SHA-256 `dbd12d55073b70add777895457040f8ede59fc1ee7198d6ae179a37087eea8bb`; prior image identities in [F provenance](../2026-10-26-native-feasibility/CANDIDATE_PROVENANCE.json) | Failed historical partial recovery; no approval to execute or promote |
| Fixture/config | Original staggered 267-ID fixture, queue capacity256, default10consumers, Linux amd64/local fsync-capable storage. [Original generated YAML](../2026-10-26-queue/guarded-baseline/generated.yaml), SHA-256 `730bb07176cf92495795809f845957b77652200a0b2bd77137079c951ab4d56b` | Immutable reference verified, not generated/run in H. Preserve original polling; diagnostic20ms overlay cannot substitute for it |
| Pipeline/storage | Freeze receiver/exporter/storage IDs, logs pipeline, feature gates, retry/admission semantics, queue sizing units, fsync setting, state format and storage path ownership | Candidate exact config, supported backend/OS, transaction semantics and failure model require review. No config change in H |
| Isolation/security | Synthetic data only; owned disposable resources; authenticated TLS API and independent PostgreSQL reader; tenant/method boundaries, non-root/resources, network/egress policy | **NOT TESTED** in H; no new runtime capability/credential readiness claimed |
| Source inventory | Producer durably inventories stable run-scoped IDs and original payload hashes before append/fsync; records admission/checkpoint cut independently of downstream success | Historical fixtures available. New fixture hash, exclusive writers, sealed windows and source retention preflight pending |
| Observer | Exact source/hash and supported observation mechanism for storage transaction IDs/pages/fsync, old/new keys, in-flight metadata, enqueue/send/ACK and checkpoints | Required candidate boundaries unverified. Timer-only kills cannot substitute; no unapproved instrumented fork |
| Budget/approvals | Named runtime/verification owners, exact commit/digests, ten-repeat cut schedule, duplicate budget, witness/drain deadlines and supported fault boundary | Broader design/qualification decisions pending. H explicitly authorizes no execution |

Before a separately authorized run, preserve the product/generator/Agent/fixture/
observer source hashes as well as binary/config identities. Validate compatible
old/new stopped state on disposable copies, never the sole backup. A failed
provisioning step must be retained as BLOCKED, not omitted from the evidence.

## Case readiness and acceptance definitions

| Case | Required setup/cuts | PASS/FAIL/BLOCKED rule | H status |
|---|---|---|---|
| N1 pinned control | Unchanged0.123.0 staggered267; ten in-flight,256 waiting, one backpressured uncheckpointed tail; API held before DB commit; baseline restart | Reproducing historical267/257/10 confirms the defect but native delivery stays **FAIL**. Record reproduction success separately. If not reproduced, investigate drift; do not infer a correction. Missing identity/cut evidence blocks interpretation | **NOT RUN / BLOCKED**: execution not authorized; archived reference is not fresh preflight |
| N2 admission durability | Empty/almost-full/full; before enqueue; payload/metadata written before commit; commit/fsync before return; after filelog checkpoint. Include failed writes/fsync and source backpressure | Every admitted record has durable reachable handoff; unsuccessful admission must not advance source beyond recoverable data. Missing admitted IDs or successful admission after failed durability is FAIL. Unobservable boundaries/unknown admission semantics are BLOCKED | **NOT RUN / BLOCKED**: no supported candidate, exact config, witnessed cut mapping or execution authorization |
| N3 saturated restart | Same267/default-size queue, SIGTERM and SIGKILL with service held before commit. Inspect10inflight+256waiting; reopen and drain | Require267distinct, no missing/unexpected IDs or unaccounted duplicates; checkpointed prefix not masked by reread. Additional queue-only cloned control quarantines source and requires266admitted before resuming tail separately. Deadlock/capacity loss is FAIL; unwitnessed saturation is BLOCKED | **NOT RUN / BLOCKED**: candidate/provenance and authorized fixture execution absent |
| N4 interrupted recovery | Fresh saturated clones; both populated legacy migration and current-schema startup; cuts below, ten repeats each, three consecutive crashes, ten clean post-drain restarts | Every committed cut must preserve admitted work; final267delivered with accounted attempts/rows. Any missing admitted ID is FAIL; a cut not exposed/certified is BLOCKED, never silently skipped | **NOT RUN / BLOCKED**: source/release, boundary observer, approval and rollback prerequisites unresolved |

Historical denominators are explicit: 267 producer-inventoried events, 266 durably
queued at saturation, one retained unadmitted tail. Queue-only and full-pipeline
results must not be mixed. A source ledger detecting lost data is not a native
recovery copy. No replay helper, checkpoint rewind or capacity increase can repair
a native FAIL and relabel it PASS.

## N4 complete cut schedule to bind to a future supported design

1. Before reading in-flight metadata; after reading payloads and before mutation.
2. Before first recovery mutation; after its committed metadata page/fsync.
3. After each replacement/metadata commit: zero, one, intermediate and all ten.
4. Before and after clearing in-flight/migration markers; before consumers resume.
5. Interrupted partial migration/restart, three consecutive crashes at the selected
   cut, then ten clean restarts after drain with stable counts.

At least ten independent repetitions per prescribed cut and positive case, using
fresh state clones and explicit cut witnesses. Existing-index designs must map
their durable ownership/completion commits to each requirement. Atomic designs
must justify named equivalent precommit/in-transaction/postcommit cuts rather
than quietly dropping obsolete per-item cuts. After a failed atomic transaction,
reopened state must be complete old or complete new, never a partly retired set.
Journal designs additionally need intent/generation/progress/authority/cleanup
cuts. No candidate-specific mappings are approved or executed in H.

The ADR's proposed budget is120seconds to witness and120seconds to drain after
the final injected fault is removed; owner review must freeze it before execution.
Unwitnessed cut: BLOCKED. Missing ID at deadline: FAIL, even if a later diagnostic
attempt recovers it. Preserve every failed/timed-out attempt and all receipt cuts.
SIGSTOP/reassert/SIGKILL needs actual committed-state/syscall evidence; elapsed
timing alone is insufficient. Process kills are not storage power-loss tests.

## Independent receipt and duplicate oracle

Persist `E`, the producer ID/payload inventory, independently of source checkpoints
and queue contents. Track admission per ID. Freeze writers and resolve outstanding
requests before a consistent PostgreSQL snapshot/watermark. Export raw IDs, row IDs,
payload hashes, timestamps, batch receipts and actual authenticated API commit-
accepted record attempts `A(i)`; separate rejected/received/uncommitted requests.
Independently query physical database rows `P(i)`, not an exporter success counter.

- Distinct persisted `D={i:P(i)>0}`; missing `E−D`; unexpected `D−E`.
- Physical rows `sum(P(i))`; physical duplicates `sum(P(i))−|D|`.
- Accepted duplicate attempts `sum(A(i))−|{i:A(i)>0}|`, reported separately.
- Every physical row links to a committed accepted request; preserve payload/tenant
  identity and check `P(i)≤A(i)`. Batch deduplication is not automatically zero
  accepted duplicate attempts or exactly-once behavior.

Require no missing admitted IDs at every accepted cut and no unexplained extras or
payload differences. Fully ACKed/no-fault controls require zero duplicates. Lost-
ACK ambiguity permits only explicitly explained resends within an owner-approved
per-case budget; an unset budget blocks acceptance. Post-drain restarts must not
increase attempts or physical rows. Preserve pre-fault, native and final receipts
so later results cannot overwrite earlier failures.

All new quantities remain null in H. N5–N8, full five-method/security compatibility,
power-loss/platform limits, CHK-002, licenses/supply chain and release decisions
remain separate even after any future N1–N4 feasibility success.
