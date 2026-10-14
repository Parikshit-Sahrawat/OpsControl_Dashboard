#!/usr/bin/env bash
# Pin workflow validation tooling; never disable TLS or trust an unchecked executable.
set -euo pipefail
cd "$(dirname "$0")/.."
private=$(mktemp -d)
trap 'rm -rf -- "$private"' EXIT
archive="$private/actionlint.tar.gz"
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
  https://github.com/rhysd/actionlint/releases/download/v1.7.7/actionlint_1.7.7_linux_amd64.tar.gz -o "$archive"
printf '%s  %s\n' '023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757' "$archive" | sha256sum --check --status
tar xzf "$archive" -C "$private" actionlint
"$private/actionlint" -shellcheck= -pyflakes= .github/workflows/v15-quality.yml .github/workflows/agent-packaging.yml .github/workflows/arch001-native-monitoring.yml
