# Accountable licensing decisions required

**BLOCKED; not legal advice, approval, or a license exception.** No reviewer has
signed any component clearance. The application has no tracked top-level
LICENSE/NOTICE defining redistribution terms. Owner must assign legal/release
reviewers and record decisions before distribution.

| Component scope | Required decision/evidence | Accountable reviewer |
|---|---|---|
| OpsControl application, worker and agent source/bundles | Choose and publish application terms; establish ownership/contributor authority and compatibility with dependencies. Decide source availability and NOTICE packaging. | Owner/legal: unassigned |
| Direct/transitive Python dependencies and CPython | Validate version-specific upstream terms and embedded/vendored components; package attribution texts. Inspect native library linkage and copyleft requirements. SBOM expression alone is insufficient. | Legal/release: unassigned |
| Debian base components, glibc/libstdc++/libacl and utilities | Review actual GPL/LGPL and alternative license expressions; identify corresponding source matching exact distributed binaries, patches and build inputs; choose valid fulfillment/source-offer method and retention/delivery process. Assess LGPL relinking/modifications. No source bundle/offer assembled here. | Legal/release: unassigned |
| Alpine/NGINX/PostgreSQL base and transitive components | Verify each component's license, copyright and notices; review any copyleft source obligations. Zero legal files found by filename heuristic is not proof of license absence or permission. | Legal/release: unassigned |
| Frontend React/other direct/transitive npm and static bundles | 189 lock entries inventoried; map actual immutable bundle contents, preserve required MIT/BSD/ISC/Apache notices and modification notices; inspect any copyleft/unknown terms. OS-level image SBOM alone does not cover bundled JavaScript. | Frontend/legal: unassigned |
| OTel Contrib 0.123.0 and evaluation 0.163.2 Go modules | Apache-2.0 upstream does not clear transitive licenses. Match every shipped module/version to upstream terms and applicable NOTICE; review incompatible/unknown terms and source obligations. | Agent/legal: unassigned |
| Node, pip, Black, compiler and CI/packaging tools | Distinguish internal build use from redistribution of tools or output; inspect bundled build output and vendoring. Tool upgrades are not a legal approval. | Build/legal: unassigned |

The machine-readable component assessment records cataloged licenses, source
metadata where available, required NOTICE/attribution/copyleft/source review,
unverified redistribution packaging and missing reviewer for every SBOM record.
Legal-file hashes prove only file presence. Authoritative upstream source retrieval,
source-offer text, complete notice assembly, actual bundle mapping, copyright
verification and human signoff remain incomplete. Unknown or compound license
expressions must be resolved rather than interpreted automatically as permissive.
