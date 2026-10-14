# Read-only pipeline adapters

The adapter registry is `backend/app/pipeline_adapters`. These implementations read provider state; they never start, stop or modify pipelines. Contract fixtures validate normalization and request construction, not genuine provider connectivity. All nine integrations require separate operator acceptance against the deployed provider version.

| Registry key | Supported interface | Required configuration | Additional configuration |
| --- | --- | --- | --- |
| PENTAHO | Existing pinned-TLS Pentaho Carte job status and job-entry results | `url`, `job_name`, `allowed_hosts`, `allowed_cidrs` | `execution_id`, `collect_logs`, `credential_ref` |
| IICS | Informatica REST v2 activity/activityLog | `base_url`, `task_id` | `credential_ref`, `credential_header` (`INFA-SESSION-ID` or `icSessionId`), pagination |
| AIRFLOW | Airflow stable REST v1/v2 DAG runs and task instances | `base_url`, `dag_id` | `api_version`, `credential_ref`, pagination |
| NIFI | NiFi asynchronous provenance search and process-group status | `base_url`, `process_group_id`, `component_ids` | `after`, `credential_ref` |
| ADF | Azure ARM Data Factory queryPipelineRuns/queryActivityruns | `base_url`, `subscription_id`, `resource_group`, `factory_name` | `after` (initial boundary), optional `before`, `credential_ref` (managed OAuth bearer), `api_version` |
| AWS_GLUE | AWS Glue SDK GetJobRuns | `region`, `job_name` | workload identity/default credential chain; optional `profile_name` |
| SSIS | Read-only SSISDB.catalog.executions | `connection_ref` | `folder_name`, `project_name`, `package_name` |
| TALEND | Talend Cloud management `/processing/executions` | `base_url` | `task_id`, `credential_ref`, pagination |
| CUSTOM | Approved local JSONL execution evidence | absolute `path`, `jobchain` | `max_bytes` |

HTTP adapters require deployment-owned `OPSCONTROL_NATIVE_ALLOWED_HOSTS`, `OPSCONTROL_NATIVE_ALLOWED_PORTS` and `OPSCONTROL_NATIVE_ALLOWED_CIDRS`. They pin the resolved IP and validate the TLS hostname. Redirects are rejected. URLs cannot contain user credentials; provider credential values are obtained exclusively from existing managed `env:` secret references. No SDK or secret is silently installed. Configure a least-privilege provider identity. Provider secrets and full error bodies are not logged.

Glue requires optional `boto3` in the worker image and an approved AWS workload identity; it does not accept AWS keys in resource JSON. SSIS requires optional `pyodbc`, the Microsoft ODBC driver and a managed connection reference. Missing dependencies produce `DEPENDENCY_UNAVAILABLE`, not a successful empty result. Use a database identity with only required SSISDB catalog read permissions; do not use a SQL Server administrator.

Custom/Shell observes JSONL emitted by the operator's existing scheduler/script. It never executes supplied shell commands. `OPSCONTROL_PIPELINE_LOG_ROOTS` is an operator-owned path-separated list of permitted read roots. A record requires `execution_id`, a timezone-aware timestamp (or start/end timestamps), and status `RUNNING`, `SUCCESS`, `FAILED` or `UNKNOWN`. Optional `record_id`, `step`, `attempt` and `execution_type` retain source semantics. Byte/inode/prefix checkpoints resume complete lines, tolerate a partial trailing line, detect rotation and truncation, and preserve identical messages at distinct file positions. Rotation files must remain available to the upstream file-log agent until acknowledged; this single-path adapter cannot recover an unread file that an external process has already deleted.

NiFi is a flow processor, not a scheduled jobchain engine. Provenance events retain flowfile/event identity and are labeled `FLOW_EVENT`. A successful SEND is not fabricated as a completed job. Explicit component IDs are required to restrict accepted events to the intended components. High-volume provenance queries can reach provider result limits; `complete=false` signals this and must not be interpreted as complete flow coverage. Provider provenance retention and query time syntax must be validated in live UAT.

Each adapter exposes `validate`, `test_connection`, `discover_capabilities`, `collect`, `collect_with_retry`, `normalize` and `health`. `Batch` contains `events`, `evidence`, `checkpoint` and `complete`. Durable runtime checkpoints must be stored separately from editable connector configuration and advanced only in the same transaction as persisted evidence. A connection test performs a real read. Capability declarations describe implemented interfaces and explicitly report `live_verified=false`; they do not assert that a configured remote platform exists.

ADF persists its bounded updated-time window across continuation pages; after completion the next poll advances from the previous window boundary. Read-only transient failures use bounded exponential backoff. Authentication, configuration, schema and TLS failures are not retried. Polling offsets/tokens, Glue continuation tokens, NiFi query IDs, SSIS execution watermarks plus active IDs and Custom byte checkpoints are returned to the existing worker. SSIS revisits nonterminal executions so a RUNNING snapshot can later become SUCCESS/FAILED. Unknown vendor statuses remain UNKNOWN. All timestamps must have source timezone information; no ingestion-time substitute is used to claim a real execution time.

Run controlled tests:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m unittest discover -s backend/tests -p test_pipeline_adapters.py -v
```

Fixtures cover all registry entries, provider statuses, pagination, retry classification, TLS/host rejection, ADF read-query request bodies, NiFi asynchronous queries, SSIS active execution replay and Custom rotation/truncation/raw-record identity. Live Pentaho, IICS, Airflow, NiFi, Azure, AWS, SSIS and Talend acceptance remains pending approved provider access.
