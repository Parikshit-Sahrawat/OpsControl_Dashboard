# Browser reload timeout investigation

Review date: 2026-11-08 (Asia/Calcutta). Execution logs retain their original UTC timestamps. Tested source `80835f0065de24ebf271fc621b6d1e5e83d73bd2`; main `ffe5ac285ab8aef33a1139bce6f3da79be3d6d33`.


**Historical timeout NOT REPRODUCED; root cause unproven; disposition PARTIAL.** Original002B browser-failed/failed-command.log waited30seconds for Search resources after reload. It lacks a route/request trace and cannot distinguish navigation, authentication, backend contention or test synchronization. Do not retroactively attribute it to the new template controls or call it fixed.

Final release repeats the original persisted resource flow and five full reloads, asserts restored #/resources/data-resources route, waits for the actual Search control and persisted resource name, and records timing/status traces. Independent final runs pass. resource-crud.json contains each before/after hash and elapsed time. Browser errors/server errors remain asserted. No timeout increase or removed assertion.

Distinct new failures: (1) new template select lacked the explicit aria-label used by DomainParameters.Field; screenshot and API trace showed a rendered panel. Added accessible names. (2) native option wait defaulted to visible, but native <option> is hidden when select closed; raw trace explicitly resolved option[value=1]62times as hidden. Changed to attached and retained selected-value assertion. (3) redacted validation contract has errors[] alongside detail='Invalid input'; corrected test assertion without changing backend redaction. Save synchronization waits for the real PATCH200 before reading persisted effective configuration. These are evidenced local defects/test fixes, not proof of the historical reload cause.

Remaining investigation needs a reproduction of the historical failure with the new sanitized route/request trace; no arbitrary duration, sleep or retry-to-green loop is adopted. All separate attempts are retained. Owner must explicitly decide whether unreproduced intermittency is non-blocking; this report does not invent that approval.


**CHK-001 FAIL · CHK-002 BLOCKED · SECURITY BLOCKED · RELEASE NO-GO.**
