# Legal/NOTICE review remains independent and pending

No legal approval, copyright authority, licence compatibility finding or exception is granted here. Original7 `licenses.json` files remain PENDING_ACCOUNTABLE_REVIEW with reviewer null. LICENSE_COMPONENT_REVIEW.csv/JSON gives an evidence pointer and pending review for each of2451 image/component records, including duplicates shipped in multiple images.

1876 records have empty/unknown declarations; this is incomplete scanner metadata, not a conclusion that code has no licence or is illegal.283 records are flagged by GPL/LGPL/AGPL/MPL/CDDL/EPL text for human review; flags are not legal interpretations. OR/AND/WITH expressions, version constraints, exceptions, vendoring and linkage must be resolved by accountable review. A permissive expression is not proof that required attribution/NOTICE is packaged.

| Scope | Required evidence / decision | Accountable authority |
|---|---|---|
|OpsControl application/agent/worker|Confirm ownership/contributor authority, approved application licence/distribution mode and compatible source/NOTICE terms. No root LICENSE/NOTICE was found at the assessed source. Do not silently introduce Apache-2.0 or any other licence.|Product/copyright owner + legal; named reviewer PENDING|
|Python direct/transitive/native dependencies and CPython|Version-specific upstream terms, vendored subcomponents, wheel metadata and actual shipped native linkage; notices and any source/relink obligations. Runtime absence of pip/Black does not clear dependencies or builder use.|Backend/legal/release; PENDING|
|Debian/Alpine base, libc/libstdc++/ACL/utilities and BusyBox|Exact binary/source/patch/build materials, GPL/LGPL/other terms, corresponding-source or valid offer/delivery method/retention, relinking where applicable. Maintain image-to-source mapping; do not infer satisfaction from SBOM alone.|Platform/legal/release; PENDING|
|PostgreSQL/gosu/entrypoint|Review PostgreSQL and every bundled dependency/utilities separately; gosu/Go module inventory and source/build provenance. Matching entrypoint scripts/source are part of review.|DB/platform/legal; PENDING|
|Frontend JS/static bundles and NGINX|Final frontend image Syft lists71 APK packages and0 npm components; require lock/build/bundle material mapping and direct/transitive attribution. NGINX/OS terms are separate. Actual licence/NOTICE files and modification/source obligations must be assembled and content-hashed.|Frontend/ingress/legal; PENDING|
|OTel0.123.0 + bundled UAT binary|Upstream Apache-2.0 does not clear935 cataloged collector records or all transitive/embedded modules. Resolve missing metadata, applicable upstream NOTICE, terms, source obligations and actual binary materials without changing the pin.|Collector/legal; PENDING|
|Builder/CI/bootstrap/legacy paths|Separate internal build use from redistributed tools/output; inventory packages and effective supply-chain/notice obligations. Existing Black/pip remediation evidence is bounded, not a global legal or security approval.|Build/legal/release; PENDING|

Required signoff fields: exact component/image/bundle identity and version; authoritative source text/hash; distribution mode; selected expression/exception basis; attribution/NOTICE/source-offer/relink obligations; delivered material hashes/locations; accountable reviewer identity/date/decision; unresolved dependencies. None is automatically signed by this assessment.

Final release needs both technical remediation and complete accountable legal review. No reviewer assignment or accepted exception is fabricated. Preserve existing terms/history while the owner decides; do not mark REVIEWED without evidence. SECURITY BLOCKED / RELEASE NO-GO.
