#!/usr/bin/env bash
# Reproducible Linux package from the approved digest-pinned distribution.
set -euo pipefail
cd "$(dirname "$0")/.."
package_dir=${OPSCONTROL_DEMO_AGENT_PACKAGES:-.demo-private/packages}
mkdir -p "$package_dir"
chmod 700 "$package_dir"
if [[ -e "$package_dir/opscontrol-agent-linux.zip" ]]; then
  echo 'Linux package already exists; preserve it. Use an explicit new output path for a rebuilt package.'
  exit 0
fi
image='otel/opentelemetry-collector-contrib:0.123.0@sha256:e39311df1f3d941923c00da79ac7ba6269124a870ee87e3c3ad24d60f8aee4d2'
private=$(mktemp -d)
container=''
cleanup() {
  if [[ -n "$container" ]]; then docker rm "$container" >/dev/null; fi
  rm -rf -- "$private"
}
trap cleanup EXIT
chmod 700 "$private"
container=$(docker create --network none "$image")
docker cp "$container:/otelcol-contrib" "$private/otelcol-contrib"
chmod 700 "$private/otelcol-contrib"
# Docker verified the approved immutable image/layers; checksum the extracted
# trusted artifact, rather than trusting a separate arbitrary downloaded binary.
digest=$(sha256sum "$private/otelcol-contrib" | cut -d' ' -f1)
python3 scripts/build-agent-package.py --os linux --runtime "$private/otelcol-contrib" --sha256 "$digest" --output "$package_dir/opscontrol-agent-linux.zip"
chmod 600 "$package_dir/opscontrol-agent-linux.zip"
