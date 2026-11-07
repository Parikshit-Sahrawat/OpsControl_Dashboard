# Mapping into OC-ETL-007 authority

Normative application schema: backend/app/etl_bindings/authority.py at the recorded baseline. No validation, TTL, trust store, permission, writer fence or enum is changed.

| Existing field | Required provider-specific evidence / source |
|---|---|
| organization_id/environment | Authorized backend-owned Job/source context; provider fields cannot choose another tenant |
| binding_id/native_job_id | Exact current STAGED temporal version and existing PipelineJob UUID; not native display text |
| platform/object_kind | PENTAHO / JOB per current schema; logical Job identity, not license to coerce every native object type |
| observed_native_id | Original native ID matching current binding and accepted runtime evidence; must not substitute a name |
| canonical_authority_id/canonical_object_key | Independently reviewed Server/repository namespace and native object/type identity. Proposed mapping requires exact-build review; Carte registration is insufficient |
| authority_aliases | Only independently proven same-authority aliases; hostname similarity/operator claim is not proof. Server/Carte aliases NOT established by fixtures |
| methods[].method_id/source_id/generation/revision | Exact current authorized backend method/source and immutable binding snapshot; old generation invalidates |
| reader_definition_hash/exact_build | Exact reader hash and verified installed provider build matched by existing reader capability contract; catalogue family invalid |
| evidence_id/payload_sha256 | Accepted same-scope AUTHENTICATED_RUNTIME original evidence with exact native/source/generation/build/hash. Synthetic fixtures do not meet genuine admission prerequisites |
| not_before/issued_at/expires_at | Offset-aware times; original evidence observation/creation inside signed window, TTL≤86400 seconds, current source/issuer/revocation valid |
| issuer_key_id/signature | Accountable externally governed Ed25519 issuer, exact approved target/build/source inventory; private key never enters OpsControl/browser |

Signature domain/canonicalization and strict field rules remain unchanged. Schedule IDs/revisions, native occurrences, execution attempts, epoch and alias-chain evidence remain in original referenced payloads/sidecar review material; no unsupported schedule/epoch field is inserted into the strict envelope. Mapping adequacy is a review prerequisite, not something signatures prove.

Synthetic issuer assurance is CONTRACT_TEST_ONLY, targets empty. The signed preview may be CONTRACT_VALID_NOT_QUALIFIED; a PROVIDER_QUALIFIED body under that key refuses. No qualified trust store is installed, genuine positive attestation/confirmation/receipt is fabricated, or database touched by offline tests.

Future qualified sequence remains: independent target/issuer approval → original accepted runtime evidence → current staged binding → separately authorized reviewer admission → exact proof-backed confirmation → exact version/generation receipt admission. Existing RBAC, reviewer/stager separation, transactional locks, fresh authorization, expiry/revocation and deferred constraints apply. Successful persistence never makes aggregate Workflow activation ACTIVE or health HEALTHY. Source replacement remains fail-closed until live cutover is independently qualified.


**Offline preparation only. Genuine qualification BLOCKED / NOT RUN. CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
