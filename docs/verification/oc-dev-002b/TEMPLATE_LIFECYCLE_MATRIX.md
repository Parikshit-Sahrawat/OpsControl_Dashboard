# Template lifecycle

| Case | Result / exact evidence |
|---|---|
| Attach/reload pin | PASS real HTTP source attachmentv1 and effective read |
| Publish newer version | PASS v2 leaves pinned v1 intact |
| Concurrent commits | PASS two actual HTTP PATCH commits returnv3/v4; originalv1 remains selected |
| Required attributes | PASS missing team makes effective.valid false; explicit resource attribute resolves it |
| Resource overrides | PASS collector interval override30 retained without replacing templatev1 |
| Invalid package/override containers | PASS HTTP422 for metrics string/collector array; unit object/list validation; no500 |
| Forged ownership/null state | PASS strict attachment-update schema; null required fields produce validation errors |
| Viewer/foreign source mutation | PASS denied before commit; shared catalogue is not an org-owned template table |
| Disabled resource/collector | PASS enabling/creating enabled collector on disabled source409; saved config does not assert healthy |
| Inactive templates | Source rejects new attachment of non-COMMITTED template; dedicated real HTTP inactive-template test NOT EXECUTED |
| Historical template packages | PASS versions1–4 remain; full current-state restore100 tables succeeds |
| Pin in ordinary UI edit |3 new helper cases prove selector; actual full ordinary-template-edit browser case NOT EXECUTED |
| Collector mapping/activation | Retained pipeline/API configuration association and unverified activation-denial paths pass; no genuine positive activation |
| Structured applicability | BLOCKED: template.scope is free text, not an approved source/OS/capability compatibility matrix; no guessed parsing |
| Immutable attachment/override history | NOT IMPLEMENTED: current attachment is mutable, original template packages preserved but selection/override timeline is not a new temporal model. Requires reviewed additive schema/convergence design; no use of audit strings as a substitute |

Required attributes/shape validation is not provider compatibility or runtime readiness. Existing activation prerequisite guards retained. No new semantic recurrence, type compatibility policy or provider permission. All new package/version tests are in final-application/api.json, test_sprint_template_configuration.py and template_attachment.test.mjs. Four new backend unit cases +3 new helper cases; counts overlap suite totals.

**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
