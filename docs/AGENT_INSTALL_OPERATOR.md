# OpsControl Agent — Operator installation guide

> For operators installing the OpsControl Agent on a known, approved host. This is not a packaging/build manual. Linux and Windows installers must be built, verified, and provisioned by an authorized release operator.

## Before you begin

1. In **Resource Management → Compute Instances**, create/save the host identity under the correct customer and non-production UAT environment.
2. Open **Agent Installation and Collector Configuration** for that host. Confirm the collector refers to that host.
3. Under **Agent Installation**, use **Check installer availability**. If an installer is not provisioned, stop and ask the release operator to publish an approved OS/architecture-specific artifact. Never install a placeholder or repurpose downloaded collector YAML.
4. Obtain the approved OpsControl ingestion origin and trusted CA/certificate. The agent requires **HTTPS with certificate verification**; `localhost` means the target host itself.
5. Ensure local administrator/sudo access to install a system service. The agent uses outbound communication; do not enable incoming SSH or open agent ports as a shortcut.

## Linux (Ubuntu / supported Linux)

1. Click **Download Linux Agent (.zip)** in Collector Details. Transfer the ZIP over an approved channel if installing on another host.
2. Verify the package source and independently approved SHA-256 digest from the release record:

   ```bash
   sha256sum opscontrol-agent-linux.zip
   unzip -l opscontrol-agent-linux.zip
   ```

3. Extract into a dedicated private working directory; inspect the included `README`, `runtime.sha256`, and `install-linux.sh`. Check the packaged runtime against its approved digest.
4. Only when ready to enroll, click **Create one-time enrollment** for this collector. The one-use token expires after **15 minutes**. Put it into a protected file on the target (not a command-line argument, shell history, shared screenshot, or public path):

   ```bash
   install -m 600 /dev/null "$HOME/opscontrol-enrollment"
   # Enter the token with a private editor; never paste it into logs.
   ```

5. From the verified extracted package directory, install with the **real trusted HTTPS origin** and protected enrollment file:

   ```bash
   chmod +x install-linux.sh
   sudo ./install-linux.sh https://YOUR-APPROVED-OPS-CONTROL-HOST "$HOME/opscontrol-enrollment"
   sudo systemctl status opscontrol-agent --no-pager
   ```

   Substitute the actual address and ensure the installer can read the enrollment file under its documented privilege model. Do not literally use the example hostname.
6. Confirm **Agent Health: CONNECTED** and reported runtime status in the collector UI. Connection requires a recent authenticated heartbeat. An installed service or successful token issuance alone is not connection verification.

If the service fails, inspect `sudo journalctl -u opscontrol-agent --no-pager -n 80` after checking logs for secrets. Do not disable TLS validation or run the runtime as root to hide file-access errors.

## Windows

1. Click **Download Windows Installer (.exe)** and copy it to the approved Windows host. This control is enabled only when an approved native Windows installer has been provisioned. A ZIP package is **not** a native EXE.
2. Verify the publisher's signature and independently approved SHA-256 checksum before executing. On the Windows host:

   ```powershell
   Get-FileHash .\opscontrol-agent-windows.exe -Algorithm SHA256
   Get-AuthenticodeSignature .\opscontrol-agent-windows.exe
   ```

   Proceed only if validation matches your release policy. Unsigned development builds require explicit UAT approval.
3. Create the one-use enrollment token in the matching Collector Details screen only when installation is ready. Store it in a private file with access restricted to administrators and the required service identity.
4. Run the verified installer as Administrator and supply the approved HTTPS backend origin and enrollment file as requested by the installer. Confirm service state:

   ```powershell
   Get-Service OpsControlAgent
   ```

5. Confirm the authenticated heartbeat in OpsControl. Native Windows service installation remains a separate target-host acceptance gate.

## After installation

- **Register securely:** enrollment is host/collector-bound and distinct from package download authorization.
- **Verify Agent Connection:** `CONNECTED`, recent authenticated heartbeat, agent/runtime versions and diagnostics must be visible. A `NOT REGISTERED` or `DISCONNECTED` status does not imply successful installation.
- **Configure, validate and approve** host monitoring methods, then explicitly **Apply Configuration**. A saved/validated YAML revision is **not** deployed.
- **Verify actual telemetry:** require fresh metrics/logs from the configured target. `NO_DATA` never means healthy.

## Download links and remote-host installation

The dashboard's package route currently requires authenticated authorization. Do **not** copy a dashboard bearer token into a shell URL or share session headers. A portable direct-download link requires a short-lived scoped package-download capability or your approved internal artifact repository; until provisioned, use an authenticated browser download and approved file transfer.

## Troubleshooting

| Symptom | Meaning / action |
| --- | --- |
| Installer not provisioned | Ask release operator to build, verify and publish the approved artifact in `OPSCONTROL_AGENT_PACKAGE_DIR`. |
| Download returns 401/403 | Reauthenticate or request the proper collector-view permission. Do not pass session secrets in a URL. |
| Agent NOT REGISTERED | Install/enroll agent on the intended host. |
| Agent DISCONNECTED | Check target service, approved HTTPS origin, certificate trust, and last heartbeat. |
| Method NOT_APPLIED | Validate and explicitly approve a revision for application after enrollment. |
| Telemetry NO_DATA | Check collection method, source permissions, exporter, and actual delivery evidence separately. |

For package maintainers and security details see [the engineering agent README](../agent/README.md).
