# OpsControl Agent

Collector is the logical Resource Management entity. OpsControl Agent is the installed host service; it supervises the pinned upstream OpenTelemetry Collector Contrib 0.123.0 runtime. It never accepts remote shell commands. One Collector binds one agent/host; each Collector can contain multiple independently identified File Log, Metric Scrape, OTLP Receiver and secured Syslog Receiver methods. Native OS Metrics uses hostmetrics. Journald and Windows Event Log are File Log source options.

## Build and download an approved package

Obtain the correct official Contrib binary for the target OS/architecture from the upstream distribution or your approved artifact repository. Verify the upstream signature/checksum through your supply-chain process. This repository's local validation uses the official Contrib Docker image pinned to digest `sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2`. It does not claim native Windows runtime acceptance.

```bash
python3 scripts/build-agent-package.py --os linux --runtime /approved/otelcol-contrib --sha256 APPROVED_SHA256 --output /private/packages/opscontrol-agent-linux.zip
python3 scripts/build-agent-package.py --os windows --runtime /approved/otelcol-contrib.exe --sha256 APPROVED_SHA256 --output /private/packages/opscontrol-agent-windows.zip
```

Do not derive `APPROVED_SHA256` from an untrusted download; use the separately approved digest. Provision `OPSCONTROL_AGENT_PACKAGE_DIR` on the backend with those exact package filenames. Collector Details then provides authenticated package downloads; unavailable packages return an error rather than pretending an installer exists. Zip archives contain the matching verified binary, supervisor, checksum, platform installer and instructions. Extract and verify `runtime.sha256` before use.

## Linux installation

1. Create an OTEL Collector for a Linux Data Source, add methods, preview/download YAML, and save a revision. Configure the server's exact compatible `OPSCONTROL_OTEL_BINARY` to obtain VALIDATED status.
2. Generate one-time enrollment in Collector Details. Transfer the token to a mode-0600 file through an approved channel. It expires in 15 minutes and is consumed once.
3. Extract the Linux package on the approved target and run locally:

```bash
chmod +x install-linux.sh
sudo ./install-linux.sh https://opscontrol.example.test /private/enrollment
sudo systemctl status opscontrol-agent
sudo journalctl -u opscontrol-agent --no-pager
```

The installer creates a dedicated unprivileged `opscontrol-agent` account, protected state and a hardened systemd service. Grant only required read permissions, for example an explicit read ACL on the application log directory. Journald may require approved membership of `systemd-journal`. Do not run the service as root to bypass a permission failure. PrivateTmp means a host's `/tmp` is not an appropriate persistent production log source.

4. In Collector Details, explicitly approve **Apply Configuration**. The agent pulls only the authorized revision, verifies its digest, opens configured files under its service identity, runs actual Collector validation, and starts the upstream runtime. Application acknowledgment and per-signal incoming evidence are shown separately. Select an earlier validated revision and explicitly approve it to roll back.

## Windows installation

Install a machine-wide supported Python 3.12 environment and its platform-only dependency:

```powershell
python -m pip install -r requirements-windows.txt
.\install-windows.ps1 -Backend https://opscontrol.example.test -EnrollmentFile C:\Private\enrollment
Get-Service OpsControlAgent
```

Run the installer locally as Administrator on the approved target. The agent service runs as LocalService. The installer restricts ACLs and grants the service account write access only to its state directory. Ensure the machine-wide Python/pywin32 service runtime is readable by LocalService. Grant explicit file-read ACLs and approved Event Log reader rights for the configured sources. Do not store enrollment or identity credentials in a public folder. Native Windows installation/runtime remains a target-host UAT gate when no Windows execution environment is available.

## Runtime and credentials

The backend URL must be an HTTPS origin with trusted certificates. Install your organization's CA through normal OS/Python and Collector trust configuration. TLS verification is never disabled. Redirects are rejected. Enrollment yields a customer/Collector-bound WorkerIdentity credential, stored once in private state (Linux mode 0600; Windows restricted ACL). The credential expires after 90 days and can be revoked from Collector Details. Re-enrollment must be explicitly authorized; existing agent and configuration history remains retained.

The supervisor sets `OPSCONTROL_AGENT_TOKEN` only in the managed process environment. YAML references `${env:OPSCONTROL_AGENT_TOKEN}`; saved YAML does not contain the value. Provision additional `env:NAME` application scrape/receiver secrets on the target service through your approved secret mechanism. Do not paste secret values into method forms.

Management errors, unreadable/nonexistent log paths, invalid Collector configuration and runtime failures are reported using bounded error codes. Private runtime diagnostics remain on the target. Connection/heartbeat state is independent of Logs, Metrics and Traces reception. NO_DATA is a valid state; an open port or saved configuration does not establish health.

## Application instrumentation

For a loopback HTTP OTLP method, set `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318` and `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` in the application SDK. For gRPC use the configured endpoint and `grpc`. Enable only the configured Logs, Metrics and/or Traces SDK exporters. Remote application listeners require explicit binding approval, TLS certificate/key and authentication; loopback is the default. The host Collector exports to OpsControl's authenticated OTLP/HTTP ingestion endpoint over HTTPS.

File Log methods need actual target files/permissions. Prometheus targets must expose compatible metrics; authentication references require TLS. Do not expose OTLP ports publicly through a firewall merely because a UI path was saved. No secure remote installation channel is implemented; host IP inventory does not authorize installation.


Agent 1.1.0 also reports configured OS service/process observations and host uptime. Configuration snapshots are revision-bound; query or permission failures remain unavailable/error evidence. Linux uses read-only systemd queries and `/proc`; Windows uses fixed SCM/tasklist queries. Collection configuration does not grant OS filesystem/service permissions. See [ARCH-001 operations](../docs/ARCH_001_OPERATIONS.md) for VM-associated onboarding and actual acceptance boundaries.
