#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo 'Run as root on the approved target.' >&2; exit 1; }
systemctl disable --now opscontrol-agent.service
rm -f /etc/systemd/system/opscontrol-agent.service
systemctl daemon-reload
# Keep credentials, file checkpoints and runtime backups for recovery/reinstall.
printf '%s\n' 'Service removed. /var/lib/opscontrol-agent and /opt/opscontrol-agent retained; revoke the Agent through OpsControl before disposing of this host.'
