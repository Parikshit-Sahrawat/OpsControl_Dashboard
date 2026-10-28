# Bounded source removal

Implementation `274175850c8553ecbf27d8cb0e7a2d9f5136a9da` from main `09a578f70282c7889a515c332c948f1940ae6719`. No applied migration edited. Provider SDK dependency removed; no collector binary/version changes. Standalone EC2/VM, API/Pentaho and shared telemetry retained.

New removal contract tests check missing routes/capabilities/adapters, rejected excluded sources and supported-source schema acceptance. This is NOT full HTTP/DB certification. Full backend suite currently fails because two obsolete modules import removed functions; security assertions were not deleted to hide this failure. Remaining input paths, historical renderer branches, test contracts and complete deployment/documentation semantics require follow-up before owner acceptance.

CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO
