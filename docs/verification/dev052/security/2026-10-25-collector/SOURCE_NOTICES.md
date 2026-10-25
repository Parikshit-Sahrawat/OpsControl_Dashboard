# Source snapshots and outstanding licensing review

The unmodified `upstream-checkpoint.go.txt`,
`upstream-checkpoint_protobuf.go.txt` and
`upstream-generated-feature-gates.go.txt` snapshots are from
`open-telemetry/opentelemetry-collector-contrib`, tag `v0.163.0`, under their original
OpenTelemetry copyright/SPDX headers. The complete upstream Apache-2.0 license is
retained as `upstream-CHECKPOINT-LICENSE.txt`; its upstream NOTICE is retained as
`upstream-CHECKPOINT-NOTICE.txt`. Source URLs and file hashes are in
`source-provenance.json` and the artifact checksum manifest. No source-file change
or authorship is asserted.

`upstream-release-manifest.yaml` is from the image-label release revision
`6c65793ec707f673304e52dfcb642684fda1a048` in
`open-telemetry/opentelemetry-collector-releases`. It connects distribution 0.163.2
to the Contrib 0.163.0 component source. Its upstream license is retained as
`upstream-RELEASE-LICENSE.txt`. Recorded image labels are provenance
metadata, not an independent signature or legal signoff.

The 2,025 component records in `license-review.json` are an inventory with explicit
review gaps. Authoritative per-version terms, transitive copyright/NOTICE mapping,
the exact notices shipped in final binaries/images/installers, modification
notices and corresponding source/offer obligations where applicable still need
accountable human review. Root legal-file enumeration is not exhaustive binary
NOTICE verification. No component is declared legally cleared.

Application LICENSE/NOTICE terms remain undecided; no application redistribution
license is inferred from dependencies or these evidence files. Assign runtime,
legal and release reviewers before any approved distribution. Prior A.2 license
decision requests remain open. No new binary is committed or distributed here.
