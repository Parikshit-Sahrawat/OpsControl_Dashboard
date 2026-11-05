# Resume and baseline delta — 2026-11-05

Original implementation started from PR #76 (8ca14f3e795d7b7039067d7025dbed3d6531fb3e), then unmerged. Current main is ee4ba0db26b5f0648677b3fe69f813128fbfaefe. PR #76 merged 2026-10-29T22:47:20Z; #74 resource-management and #75/#77 UAT automation also merged. Integration commit: fa3a9a24107f465dac6692b2a9ea69b910ff06ee. No conflict; no reset or overwrite of task evidence.

The environment reset cleared /tmp: unfinished v16-final/backend/build runs from October have no retained exit status and are NOT TESTED at that attempted revision. Preserved raw/ files are the completed prior runs, including failures. New runs are raw/resumed/; no inference from missing logs.

PR #74 changes compute resource identity, onboarding, operational UI and pagination test contracts. `docs/uat/GLOBAL_UAT_REGISTER_2026-10-28.md` records an approved eight-step journey and RM-DEF-001–039, with observed Ubuntu connection/metrics but unresolved acceptance, Windows artifact, duplicate telemetry, performance and journald findings. Earlier ten-stage browser evidence is historical, not acceptance of this newer journey. No UAT finding closes on merge alone. The new global UI-001–010 labels collide with canonical older UI IDs: retain them as document-qualified UAT labels; do not silently replace approved UI-001–023 definitions. Owner must reconcile intended scope/version.

PRs #75/#77 supply deployment implementation and recorded activation evidence; previous statements that controller implementation is absent are superseded. This task does not activate the poller or independently certify live host state. Stage B unit tests do not equal live deployment acceptance.

Current product delta of this task remains profile/preferences, Help, Alerts labels, responsive account controls and isolated fixtures. Canonical architecture inventory and Kubernetes removal audit are not repeated. New UAT authority does not grant this task access to live UAT. Remaining RM-DEF acceptance and runtime investigations are explicit limitations; no full-development completion claim.

UI-004 is explicitly SUPERSEDED: the approved eight-step journey replaces its ten-step prescription. This does not mark replacement behavior ACCEPTED; current workflow acceptance remains open.
