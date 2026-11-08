# Development-program workflow display names

Owner-requested follow-up to PR85. All27 GitHub Actions display names use `OC Dev - Tier A–F - Purpose`, based on the approved ten-sprint program. Historical ARCH001/V1.5/V1.6/Phase1 labels are removed from the Actions list. Names describe verification scope, not sprint completion, formal owner UAT or release certification.

A: fast/source/controller policy. B: real-component integrated verification. C: shared security and image evidence. D: separately invoked controlled/provider/packaging tests. F: independently gated release/UAT operations. No workflow is relabeled as TierE sprint-exit certification because a complete sprint-exit qualification workflow does not exist. Missing later-sprint capabilities remain missing; renaming creates no new acceptance evidence.

[NAMES.json](NAMES.json) maps every previous/new name and unchanged job IDs. Only top-level `name` changes: workflow paths, job/check names, triggers, permissions, environments, conditions and test commands are unchanged. All13 protected check contexts remain preserved. Release verification checks workflow paths, not these display labels. No existing CI evidence inventory is overwritten.

Local validation: semantic before/after equality excluding top-level name; unique names; all-workflow actionlint; existing CI policy and90 controller/CI regression tests (including23 focused CI cases). Logs and exit codes accompany this record. Hosted CI is triggered at push/PR update; results are not polled.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO. No merge, deploy, publication or activation.
