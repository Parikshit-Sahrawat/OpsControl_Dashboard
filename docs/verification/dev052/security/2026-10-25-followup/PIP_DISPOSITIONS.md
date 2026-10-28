# Six pip dispositions — 2026-10-25

All six are **UNRESOLVED overall**; reviewer: automated technical assessment by
Codex, accountable security/release reviewer **not assigned**. No exception.
Runtime pip/ensurepip absence is verified for the final Python candidates. The
declared Linux build/bootstrap scope is patched and tested, not every operator
or historical/native platform path. Full individual records, including original
severity/aliases and previous Black dispositions, are in
`nine-advisory-dispositions.json`.

| Advisory / CVE | Path and listed fixed version | Evidence-backed disposition |
|---|---|---|
| PYSEC-2026-196 / CVE-2026-8643 | Malicious entry-point install path; 26.1.2 | Verified 26.2 bootstrap precedes dependency installs in patched paths. Package trust still matters; native/legacy execution incomplete. UNRESOLVED overall. |
| PYSEC-2026-1795 / CVE-2025-8869 | Tar symlink fallback; 25.3 | Python 3.12 data_filter is present and installer is 26.2. No exemption for arbitrary older operator/platform paths. UNRESOLVED overall. |
| PYSEC-2026-1796 / CVE-2026-1703 | Wheel extraction; 26.0 | The fixed reviewed wheel executes its own installer; old installed pip does not extract it. Linux online/offline tests passed; full legacy/native matrix incomplete. UNRESOLVED overall. |
| PYSEC-2026-2875 / CVE-2026-3219 | Ambiguous archive; 26.1 | Bootstrap selects a fixed wheel/hash with no resolver/index; subsequent patched installs use 26.2. Operator/archived paths remain to review. UNRESOLVED overall. |
| PYSEC-2026-2876 / CVE-2026-6357 | Self-update import; 26.1 | Old pip is not invoked. Verified wheel starts under `-I`; final stages remove old tooling without invoking uninstall. Python site/OS trust and native coverage remain review inputs. UNRESOLVED overall. |
| PYSEC-2026-3721 / CVE-2026-13346 | Doubly encoded index URL; 26.2 | Fixed HTTPS wheel URL and SHA-256; patched dependency installer is 26.2. No clearance for unexecuted index/operator/platform configurations. UNRESOLVED overall. |

Changed Windows packaging and Kubernetes install paths are NOT TESTED natively.
Legacy demo/UAT and golden-path Docker changes received source/context review,
not full stack execution. Existing baseline harness archived by DEV051 remains
historical; immutable historical scripts/evidence were not rewritten to claim a fix.
Manual installation instructions and independently provisioned environments need
accountable review. Patched CI YAML validates; hosted workflows were not manually
rerun. Neither a fixed installer nor a successful package install constitutes a
complete build-environment security clearance.
