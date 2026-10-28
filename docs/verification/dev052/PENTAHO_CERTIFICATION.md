# Genuine Pentaho certification runbook — approval required

Current status: **BLOCKED**. No approved runtime binding, credentials, CA,
installation or owner-approved target was supplied. No fresh native test ran.
Historical RT-LAB reconciliation is not fresh certification. Never substitute the
synthetic Docker Carte fixture or a version-family catalogue entry.

## Required owner inputs

Provide authorization covering the exact isolated lab, operator, time window,
read-only API paths and allowed workload execution; exact PDI/Carte/Pan/Kitchen
build, OS/Java, binary hashes, license/entitlement, server restart epoch authority,
CA chain/hostname, scoped read-only account through secure environment settings,
host/CIDR allowlists, benign success/failure job and transformation files with
hashes, scheduler retry authority, and a disposable OpsControl organization/DB.
Local desktop/Windows paths in historical reports do not establish cloud access.
Do not request secret values in chat or connect to guessed endpoints.

## Reproducible operator sequence after approval

1. Create a restricted evidence directory (`umask 077`). Record source commit,
   installed build output, Java/OS, executable/workload hashes, UTC clock and
   timezone, source/customer/method IDs and restart epoch. Compare with the
   approved inventory; stop on an unverified mismatch.
2. Establish verified HTTPS and least-privilege auth using only approved GET
   status paths for that exact installed build. Keep raw XML/logs private until
   redaction. Example on the approved host, with securely configured variables:

   ```sh
   curl --fail --silent --show-error --cacert "$LAB_CA" --netrc-file "$LAB_NETRC" \
     --get "$LAB_CARTE/kettle/jobStatus/" \
     --data-urlencode "name=$LAB_JOB" --data-urlencode "id=$LAB_EXECUTION_ID" \
     --data-urlencode 'xml=Y' --output "$PRIVATE_EVIDENCE/job-status.xml"
   ```

   Verify the build-specific transformation/status paths independently. Do not
   invoke start/stop/remove/control APIs. Do not disable hostname/TLS checks.
3. An independently authorized lab owner runs benign success/failure job and
   transformation fixtures using installed Pan/Kitchen. Example shape only:
   `pan.sh -file=/approved/lab/success.ktr -level=Basic` and
   `kitchen.sh -file=/approved/lab/success.kjb -level=Basic` (Windows equivalents
   require their own native validation). Capture exit code and native logs, not
   credentials. Repeat with independently approved failure fixtures. These are
   workload executions requiring separate permission; OpsControl remains read-only.
4. Observe through the actual OpsControl reader/agent and persist evidence. Assert
   native execution identity, success/error indicators, event vs discovery times,
   parsed logs/steps, source generation and append-only history. Exit 0 alone,
   HTTP 200 or missing telemetry must never imply ETL success. Compare native and
   OpsControl outcomes using exact IDs, including restart/retry relationships.
5. Test wrapper boundary (CLI execution external to monitoring), secrets redaction,
   granular RBAC, cross-customer denial, hostname/untrusted-CA failures and
   disallowed paths/methods. Never send production credentials to negative targets.
6. Fill every matrix row with expected/actual, command, native IDs, timestamps,
   hashes, reviewer and PASS/FAIL/BLOCKED/NOT TESTED. Independent reviewer signs
   exact-build/method capability; do not generalize across builds or OSes.
7. Export redacted logs/screenshots/machine-readable results before removing only
   owned disposable test accounts, secret files and lab resources. Record cleanup.

## Fresh certification matrix

| Gate | Carte | Pan transformation | Kitchen job |
| --- | --- | --- | --- |
| Exact build/OS/Java/license and binary hashes | BLOCKED | BLOCKED | BLOCKED |
| Auth/TLS/hostname and source policy | BLOCKED | BLOCKED (agent transport) | BLOCKED (agent transport) |
| Genuine native success and failure | BLOCKED | BLOCKED | BLOCKED |
| Native identity, timestamps and status/log parsing | BLOCKED | BLOCKED | BLOCKED |
| Wrapper/monitoring-only boundary and restart/retry authority | BLOCKED | BLOCKED | BLOCKED |
| Persisted OpsControl evidence, RBAC and tenant isolation | BLOCKED | BLOCKED | BLOCKED |
| Secret redaction, negative cases and cleanup | BLOCKED | BLOCKED | BLOCKED |

Cloud and native Windows certification need separate approved identities/hosts.
Kubernetes monitoring remains deferred; no scope approval was provided.
