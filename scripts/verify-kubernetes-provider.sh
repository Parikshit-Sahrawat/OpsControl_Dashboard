#!/usr/bin/env bash
# Disposable kind cluster only; verifies real Kubernetes API reads and least privilege.
set -euo pipefail
ns="opscontrol-provider-ci"
trap 'kubectl delete namespace "$ns" --ignore-not-found --wait=false >/dev/null 2>&1 || true' EXIT
kubectl create namespace "$ns"
kubectl -n "$ns" create serviceaccount monitoring-reader
cat <<'YAML' | kubectl -n "$ns" apply -f -
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: monitoring-read-only
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get","list","watch"]
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get","list","watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: monitoring-read-only
subjects:
  - kind: ServiceAccount
    name: monitoring-reader
    namespace: opscontrol-provider-ci
roleRef:
  kind: Role
  name: monitoring-read-only
  apiGroup: rbac.authorization.k8s.io
YAML
kubectl -n "$ns" create deployment demo-web --image=python:3.12-alpine -- python -m http.server 8080
kubectl -n "$ns" rollout status deployment/demo-web --timeout=180s
pod="$(kubectl -n "$ns" get pods -l app=demo-web -o jsonpath='{.items[0].metadata.name}')"
identity="system:serviceaccount:$ns:monitoring-reader"
assert_permission(){
  expected="$1"; verb="$2"; resource="$3"; namespace="$4"
  observed="$(kubectl auth can-i "$verb" "$resource" --namespace "$namespace" --as "$identity" 2>&1 || true)"
  echo "RBAC: $verb $resource in $namespace → $observed (expected $expected)"
  if [[ "$observed" != "$expected" ]]; then
    echo "RBAC expectation failed" >&2
    exit 1
  fi
}
assert_permission yes get pods "$ns"
assert_permission yes get deployments.apps "$ns"
assert_permission no delete pods "$ns"
assert_permission no list secrets "$ns"
assert_permission no get pods default
python3 -m pip install 'kubernetes>=32,<37' --quiet
PYTHONPATH=backend OPSCONTROL_TEST_NAMESPACE="$ns" OPSCONTROL_TEST_POD="$pod" python3 - <<'PY'
import os
from kubernetes import client,config
from app.worker.provider_checks import kubernetes_health
config.load_kube_config()
ns=os.environ["OPSCONTROL_TEST_NAMESPACE"]
pod=os.environ["OPSCONTROL_TEST_POD"]
observed=kubernetes_health({"namespace":ns,"pod_name":pod},client)
assert observed["outcome"]=="SUCCESS" and observed["ready"],observed
deployment=kubernetes_health({"namespace":ns,"deployment_name":"demo-web"},client)
assert deployment["outcome"]=="SUCCESS" and deployment["available_replicas"]>=1,deployment
print("REAL DISPOSABLE KUBERNETES POD AND DEPLOYMENT PROVIDER ACCEPTANCE PASS")
PY
