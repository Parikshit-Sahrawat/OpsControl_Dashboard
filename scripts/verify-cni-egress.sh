#!/usr/bin/env bash
# Run ONLY in a disposable, authorized Kubernetes test cluster with CNI
# NetworkPolicy enforcement enabled. No production namespace is modified.
set -euo pipefail
command -v kubectl >/dev/null
ns="opscontrol-egress-test-$(date +%s)"
kubectl create namespace "$ns"
cleanup(){ kubectl delete namespace "$ns" --wait=false --ignore-not-found >/dev/null 2>&1 || true; }
trap cleanup EXIT
kubectl -n "$ns" run allowed --image=python:3.12-alpine --restart=Never \
  --labels="app=allowed" --command -- python -m http.server 8080 --bind 0.0.0.0
kubectl -n "$ns" run denied --image=python:3.12-alpine --restart=Never \
  --labels="app=denied" --command -- python -m http.server 8080 --bind 0.0.0.0
kubectl -n "$ns" run agent --image=python:3.12-alpine --restart=Never \
  --labels="app=agent" --command -- sleep 3600
for pod in allowed denied agent; do
  kubectl -n "$ns" wait --for=condition=Ready "pod/$pod" --timeout=180s
done
cat <<EOF | kubectl -n "$ns" apply -f -
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: opscontrol-egress-test }
spec:
  podSelector:
    matchLabels: { app: agent }
  policyTypes: [Ingress, Egress]
  ingress: []
  egress:
    - to:
        - podSelector: { matchLabels: { app: allowed } }
      ports:
        - protocol: TCP
          port: 8080
EOF
allowed_ip="$(kubectl -n "$ns" get pod allowed -o jsonpath='{.status.podIP}')"
denied_ip="$(kubectl -n "$ns" get pod denied -o jsonpath='{.status.podIP}')"
echo "Waiting for CNI policy propagation ..."
sleep 12
kubectl -n "$ns" exec agent -- python -c 'import socket,sys; c=socket.create_connection((sys.argv[1],8080),timeout=5); c.close()' "$allowed_ip"
if kubectl -n "$ns" exec agent -- python -c 'import socket,sys; c=socket.create_connection((sys.argv[1],8080),timeout=4); c.close()' "$denied_ip"; then
  echo "FAIL: CNI allowed forbidden east-west egress" >&2
  exit 1
fi
echo "PASS: Real CNI allowed approved target and blocked forbidden pod."
