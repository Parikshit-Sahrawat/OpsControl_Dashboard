#!/usr/bin/env bash
set -euo pipefail
# Run locally on the approved target; never fetch remote shell code.
if [[ ${EUID} -ne 0 ]]; then echo 'Run with sudo on the approved target.' >&2; exit 1; fi
if [[ $# -ne 2 ]]; then echo 'Usage: install-linux.sh HTTPS_BACKEND ENROLLMENT_FILE' >&2; exit 1; fi
agent_backend=$1
agent_enrollment=$2
[[ $agent_backend =~ ^https://[a-zA-Z0-9.-]+(:[0-9]+)?/?$ ]] || { echo 'HTTPS origin required' >&2; exit 1; }
agent_package=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
python3 --version
[[ -f "$agent_package/otelcol-contrib" ]] || { echo 'Verified bundled OTel binary missing' >&2; exit 1; }
(cd "$agent_package" && sha256sum -c runtime.sha256)
"$agent_package/otelcol-contrib" --version | grep -q '0.123.0' || { echo 'Unsupported runtime version' >&2; exit 1; }
[[ -f /var/lib/opscontrol-agent/identity.json || -r "$agent_enrollment" ]] || { echo 'Enrollment file required for new installation' >&2; exit 1; }
command -v systemctl >/dev/null || { echo 'systemd is required' >&2; exit 1; }
if systemctl is-active --quiet opscontrol-agent; then systemctl stop opscontrol-agent; fi
if [[ -d /opt/opscontrol-agent ]]; then
  agent_backup=$(mktemp -d /opt/opscontrol-agent-backup.XXXXXXXX)
  cp -a /opt/opscontrol-agent/. "$agent_backup/"
  printf 'Previous binaries retained at %s\n' "$agent_backup"
fi
id opscontrol-agent >/dev/null 2>&1 || useradd --system --home-dir /var/lib/opscontrol-agent --shell /usr/sbin/nologin opscontrol-agent
install -d -m 755 /opt/opscontrol-agent
install -d -o opscontrol-agent -g opscontrol-agent -m 700 /var/lib/opscontrol-agent
install -m 755 "$agent_package/otelcol-contrib" /opt/opscontrol-agent/otelcol-contrib
install -m 644 "$agent_package/opscontrol_agent.py" /opt/opscontrol-agent/opscontrol_agent.py
install -m 644 "$agent_package/service_health.py" /opt/opscontrol-agent/service_health.py
if [[ ! -f /var/lib/opscontrol-agent/identity.json ]]; then
  install -o opscontrol-agent -g opscontrol-agent -m 600 "$agent_enrollment" /var/lib/opscontrol-agent/enrollment
fi
cat > /etc/systemd/system/opscontrol-agent.service <<EOF
[Unit]
Description=OpsControl Agent (managed OpenTelemetry)
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
User=opscontrol-agent
Group=opscontrol-agent
ExecStart=/usr/bin/python3 /opt/opscontrol-agent/opscontrol_agent.py --home /var/lib/opscontrol-agent --backend ${agent_backend} --runtime /opt/opscontrol-agent/otelcol-contrib --enrollment-file /var/lib/opscontrol-agent/enrollment
Restart=on-failure
RestartSec=10
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ReadWritePaths=/var/lib/opscontrol-agent
UMask=0077
[Install]
WantedBy=multi-user.target
EOF
systemd-analyze verify /etc/systemd/system/opscontrol-agent.service
systemctl daemon-reload
systemctl enable --now opscontrol-agent
systemctl status --no-pager opscontrol-agent
printf '%s\n' 'Grant only required file-read or journal group permissions to opscontrol-agent. Saving a log path does not grant OS access.'
