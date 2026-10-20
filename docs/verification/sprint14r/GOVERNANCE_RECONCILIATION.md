# Governance sources and owner decisions

Reconciliation date:20October2026 UTC. This is a controlled record of supplied decisions, not recovery of missing discussion transcripts. No earlier approval date is invented. Existing approved architecture files are unchanged.

| Source / decision | Provenance and approval | Controlled record / unresolved wording |
| --- | --- | --- |
| ARCH-001 / ARCH-ETL-001 V1.6 | Existing approved repository documents | [ARCH-001](../../ARCH_001_V16.md), [ETL](../../architecture/ARCH_ETL_001_V16.md), unchanged |
| Product Alignment | Owner confirms approval in planning discussions; reaffirms20Oct2026 | [Reconciled addendum v0.1](../../architecture/PRODUCT_ALIGNMENT_ADDENDUM.md); full original wording/date unavailable |
| OPS-DEPLOY-001 | Owner confirms approval and private-network/self-hosted requirements20Oct2026 | [Reconciled deployment decisions](../../architecture/OPS_DEPLOY_001.md); actual topology/OS builds/CA/vendor acceptance open |
| ENG-001 | Owner reports planning approval; directs bounded work under repository requirements | [Partial engineering reconciliation](../../engineering/ENG_001.md); full policy wording and compliance remain UNVERIFIED |
| Revised12–42 /14R | Owner calls revised framework approved; original detailed roadmap remains unavailable | [Conditional execution/evidence assignments](ROADMAP_RECONCILIATION.md); current14R only is implementation authorization, full original roadmap compliance UNVERIFIED |
|18 OC-IMP proposals | Kickoff calls them approved proposals; historical Sprint12 records individual approval as proposed | Preserve exact18 definitions in [original baseline](../arch-etl-001-v16-r1/sprint12/OC_IMP_V20_BASELINE.md). Current owner declaration supports requirements-level approval; per-entry approval revision/wording needs confirmation. No automatic runtime authorization for all18. |
| Historical IMP001–062 | Owner previously confirmed original unavailable; no recovered source now | All62 SOURCE_NOT_RECOVERED in [Sprint11 register](../arch-etl-001-v16-r1/sprint11/IMPROVEMENT_REGISTER.md); eight titles alone do not define requirements |

## Bounded source search

Tracked main documentation, all locally discoverable origin refs and explicitly accessible previous audit/UAT archives contain no named ENG-001, Product Alignment Addendum, OPS-DEPLOY-001 or14R source. GitHub issue search initially returned422 because an explicit issue qualifier was required; corrected `is:issue repo:Parikshit-Sahrawat/OpsControl_Dashboard` searches for each of the four names succeeded with zero matches. Owner then confirmed the documents were planning decisions rather than verified repository sources. Stop further source discovery; do not infer missing approval from unavailable text. Sanitized search results are retained with verification evidence.

## Owner-input register

| ID | Question / recommendation | Approval boundary / status |
| --- | --- | --- |
|14R-D01 | Confirm reconciled Product/OPS summaries reflect supplied decisions; supply original date/revision if recovered | Decisions approved; wording reconciliation awaiting review, no certification |
|14R-D02 | Confirm complete ENG-001 clauses, mandatory thresholds and exception procedure | OPEN; do not claim full compliance |
|14R-D03 | Confirm exact requirement-level approval revision for18 OC-IMP entries | OWNER DECLARATION RECORDED; do not rewrite historical proposed status or execute unrelated entries |
|14R-D04 | Approve explicit many-customer resource association/attribution/revocation design before implementation | OPEN; no new shared-resource runtime/schema authorized |
|14R-D05 | Supply actual private topology, CA/credential provider, Windows/Linux/container versions, proxy/VPN/vendor policy and witness | OPEN; production network/CrowdStrike/Zscaler compatibility UNVERIFIED |
|14R-D06 | Authorize read-only genuine Pentaho installed-build RT001–020 workflow and independent witness | OPEN; all20 NOT RUN |
|14R-D07 | Independent UAT of exact UI revision, including assistive technology and all affected flows | OPEN; automated synthetic evidence is preparation |
|14R-D08 | Review remaining roadmap wording, estimates and external/post42 dependencies | OPEN; no guarantee of production certification by42; no next sprint begins |

Authority precedence: approved architecture remains controlling. The current owner instructions authorize scoped decisions/work, not silent architecture replacement. Unresolved wording is explicit and cannot be silently promoted to verified compliance.
