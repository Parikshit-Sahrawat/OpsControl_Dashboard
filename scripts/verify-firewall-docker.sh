#!/usr/bin/env bash
# Disposable Docker bridge isolation: verifies network-layer behavior, not Kubernetes CNI.
set -euo pipefail
name="opscontrol-netverify-$$"
allowed="$name-allowed"
denied="$name-denied"
image="public.ecr.aws/docker/library/python:3.12-alpine"
cleanup() {
  docker rm -f "$name-ok" "$name-blocked" >/dev/null 2>&1 || true
  docker network rm "$allowed" "$denied" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker network create --internal "$allowed" >/dev/null
docker network create --internal "$denied" >/dev/null
docker run -d --rm --name "$name-ok" --network "$allowed" "$image" \
  python -m http.server 8080 --bind 0.0.0.0 >/dev/null
docker run -d --rm --name "$name-blocked" --network "$denied" "$image" \
  python -m http.server 8080 --bind 0.0.0.0 >/dev/null
sleep 3
docker run --rm --network "$allowed" "$image" python -c '
import socket,sys
ok=sys.argv[1]; blocked=sys.argv[2]
socket.create_connection((ok,8080),timeout=5).close()
for host,port in ((blocked,8080),("1.1.1.1",443)):
  try:socket.create_connection((host,port),timeout=3)
  except (OSError,TimeoutError):pass
  else:raise SystemExit("FAIL: Unapproved network egress succeeded: "+host)
print("PASS: Docker network firewall permits only the explicitly joined private segment.")
' "$name-ok" "$name-blocked"
