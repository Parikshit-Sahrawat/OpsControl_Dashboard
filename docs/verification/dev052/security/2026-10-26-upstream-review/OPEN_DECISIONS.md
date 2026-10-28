# Accountable decisions and next authorization

**No fabricated signoffs.** User authorizes G research, unpublished draft,
documentation, commit/push and internal Issue68/draftPR69 updates. The user does
not authorize upstream contact, implementing any design, building a fork/custom
binary, running N1–N4 in G, or transitioning production. This package is prepared
for review, not accepted architecture.

The existing [governance decision](https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/issues/68#issuecomment-6414180530)
names **Parikshit** as both collector/runtime engineering owner and independent
verification owner for the bounded isolated feasibility study. That role coverage
is recognized; it does not supply upstream support, a custom-build approval,
product integration approval or release signoff. Other accountable individuals
are not assigned by this report.

| Decision | Accountable role / known person | Current state and required record |
|---|---|---|
| Exact public text and target | User / repository owner | **PENDING separate explicit approval** to submit [MAINTAINER_ISSUE_DRAFT.md](MAINTAINER_ISSUE_DRAFT.md) to the core exporterhelper bug-report target; include approved draft hash, any permitted attachments, submitter and communication scope |
| Upstream triage/design ownership | Core exporterhelper codeowners: Bogdan Drutu, Dmitrii Anoshin, Collector approvers | **PENDING, not contacted/assigned**. Ask for invariant, smallest supported design and issue/PR linkage; names indicate recorded ownership only |
| Storage atomicity/durability and errors | Core storage owner `swiatekm`; Contrib file-storage owners `swiatekm`, `VihasMakwana` | **PENDING**, including backend guarantees, fsync failure outcome and rollback support; no commitment implied |
| Supported candidate/release | Upstream design/release owners | **BLOCKED** until exact maintained source/release, artifact mapping, support window and migration limits are supplied; open draft POC is insufficient |
| Local design and observed transaction boundaries | Collector/runtime engineering owner: Parikshit for approved isolated study | **PENDING review** of this exact design/evidence commit; no custom source or binary approval exists |
| Later N1–N4 qualification | Verification owner: Parikshit for approved isolated study; user for new scope | **NOT RUN in G**. Return any candidate for scoped qualification authorization; freeze candidate/observer identities, ten-repeat cuts, failure budgets and receipt oracle first |
| Commit/ACK/duplicate contract | API/data-persistence owner, name pending | **PENDING** supported commit semantics and explicit duplicate/order budget; no backend change in G |
| Recovery/retention/fault boundary | SRE/operations owner, name pending | **PENDING** source/storage retention, failure model, operator escalation and rollback SLOs; no production replay integration |
| Alternative if support remains unavailable | Runtime, source/ingestion, operations and release owners | **PENDING separate ADR decision**: approved maintainable native correction versus complete enforceable production bounded replay; neither is approved implicitly |
| Supply-chain/security and release | Security/supply-chain and release/change owners, names pending | **SECURITY BLOCKED / RELEASE NO-GO**; independent gates cannot be waived by this package |

Any approval record must name person and role, exact commit/digests, scope, date,
conditions and decision. An upstream author's test claim, an old intention to
merge an adjacent PR, a GitHub codeowner entry or an approval to research does not
fill those fields. There is no recorded upstream rejection of this proposal;
uncertain support must not be described as a refusal.

## Recommended next narrowly scoped task

After the user approves the exact draft/target, submit **one** redacted core issue
requesting invariant/design triage and a supported correction path. Before that
submission, refresh duplicate search and target form, have the authorized human
review the final public text, and do not attach the internal raw evidence bundle.
No statements of human authorship or maintainer signoff may be invented.
This recommendation is not permission to post, tag maintainers or send messages
now. No issue URL exists for this unsubmitted package.

If a supported correction is supplied, return its immutable source/distribution
and support evidence for a new qualification decision; no automatic execution.
If only an unmerged/custom proposal is offered, obtain explicit maintenance,
source/build and test authorization before touching a binary. If support is
declined or remains uncertain, document that response and reopen the accountable
ADR choice. Production replay would require complete durable source inventory,
enforced retention, independent gap detection and bounded idempotent recovery;
the existing three finite replay successes do not establish that contract.

**Unchanged gates: CHK-001 FAIL; CHK-002 BLOCKED; SECURITY BLOCKED; RELEASE NO-GO.**
Keep PR69 draft. No publication, deployment, merge, waiver or DEV-05.2B.
