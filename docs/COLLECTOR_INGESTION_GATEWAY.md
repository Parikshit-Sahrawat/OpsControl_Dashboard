# Local Agent ingestion gateway

The local Docker stack includes `ingestion-gateway`, a TLS reverse proxy on
`https://localhost:8443`. It forwards only `/api/v1/agent/` and `/health` to the
internal FastAPI service. Enrollment uses the backend's expiring one-use token;
subsequent heartbeats, configuration requests, credential renewal and OTLP ingestion
use the backend's authenticated Agent credentials. The proxy preserves the bearer
header. TLS does not replace Agent authentication.

Resource and Access Management APIs are not exposed through this listener. The
existing frontend and administration API remain bound to loopback ports 5173 and
8000 for local development. This configuration does not publish a remote service.

## Start and verify

From the repository root, with Docker Compose, Python 3 and OpenSSL installed:

```bash
bash scripts/demo-up.sh
curl --cacert .demo-private/gateway/ca.crt https://localhost:8443/health
docker compose -f docker-compose.demo.yml ps ingestion-gateway
```

The startup script generates and verifies a private local development certificate
authority and a server certificate with `localhost`, `ingestion-gateway`,
`127.0.0.1` and `::1` subject alternative names. Existing valid material is reused.
Partial, mismatched or near-expiry material causes startup to stop; it is not
silently replaced. Certificates reside in ignored `.demo-private/gateway/`.
Private keys have mode 0600 and their directory has mode 0700. The gateway receives
only its leaf certificate and leaf key, not the CA private key.

Set a different loopback listener before startup when port 8443 is occupied:

```bash
OPSCONTROL_GATEWAY_PORT=9443 bash scripts/demo-up.sh
```

`demo-up.sh` sets `OPSCONTROL_PUBLIC_INGESTION_URL` to the matching HTTPS origin.
When invoking Compose directly, supply that variable explicitly if the port changes.
Changing this URL requires saving, validating and explicitly applying a new Agent
configuration; restarting the UI does not deploy a configuration.

## Trust the development CA on the Agent host

Copy **only `ca.crt`** to the testing host over an approved channel. Never distribute
`ca.key`, `tls.key`, enrollment tokens or Agent identity files in repository content.
Verify the CA fingerprint against the operator's original:

```bash
openssl x509 -in .demo-private/gateway/ca.crt -noout -fingerprint -sha256
```

For a Linux test host, install the CA through its normal operating-system trust
mechanism, or configure both the Python Supervisor and bundled Go Collector with
`SSL_CERT_FILE=/absolute/path/to/ca.crt`. For a systemd installation, add that
variable using `systemctl edit opscontrol-agent`, then reload and restart the service:

```ini
[Service]
Environment=SSL_CERT_FILE=/etc/opscontrol/local-development-ca.crt
```

The CA file must be readable by the Agent service account. Protect the Agent's
private home, credentials and checkpoints separately. Do not use TLS verification
bypass flags.

For a Windows testing host, import the verified public CA certificate into the
Local Machine trusted root store using an administrator PowerShell session so both
the Windows Service Supervisor and Contrib runtime can validate it:

```powershell
Import-Certificate -FilePath .\ca.crt -CertStoreLocation Cert:\LocalMachine\Root
```

Use this private development CA only on authorized testing hosts. Record the
certificate thumbprint and remove this exact certificate when the local test ends.
Native Windows trust-store and Service verification require a Windows machine;
Linux Docker validation does not prove those operations worked.

## DNS and remote hosts

The default listener is loopback-only. `localhost` means the machine where the
Agent runs, so it cannot identify a separate Docker host. For a remote laboratory,
provide an explicitly approved secure route, matching DNS name and certificate,
then set `OPSCONTROL_PUBLIC_INGESTION_URL` to that address. Before creating fresh
local certificate material, additional literal DNS names can be included with:

```bash
python3 scripts/init-demo-gateway.py --directory /private/new-gateway-pki \
  --dns-name monitoring-lab.example.test
```

This command neither publishes the listener nor deploys remote software. Preserve
and verify a backup before renewing or replacing existing development TLS material.
No production certificate or trust-store changes are performed by these scripts.

## Collection state and quiet logs

Saving configuration is not deployment. Deployment is not evidence of receipt.
The backend reports method deployment, runtime observation, actual receipt counts
and timestamps independently. A readable quiet file with fresh authenticated Agent
observations can be `IDLE`; it is never labeled `RECEIVING` without persisted log
records. Missing files, inaccessible paths and protected Agent-private paths report
errors. Configuration checkpoints remain in the private Agent home through compatible
rollouts and restarts.

## Isolated verification

```bash
python3 scripts/gateway-smoke.py
```

The smoke test generates temporary TLS material and owns its temporary Docker
network and containers. It verifies chain and hostname validation, rejection of an
untrusted CA, rejection of missing/incorrect bearer authentication by a controlled
backend, correct bearer forwarding and exclusion of administration routes. It does
not touch existing Docker database volumes. The full application Docker acceptance
suite separately verifies actual FastAPI enrollment and telemetry persistence.
