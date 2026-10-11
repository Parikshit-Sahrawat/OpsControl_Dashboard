#!/usr/bin/env bash
# Disposable kind cluster only; verifies real Kubernetes API reads and least privilege.
set -euo pipefail
ns="opscontrol-provider-ci"
node="$(kubectl get nodes -o jsonpath='{.items[0].metadata.name}')"
node_role="opscontrol-provider-ci-node"
trap 'kubectl delete clusterrolebinding opscontrol-provider-ci-node --ignore-not-found >/dev/null 2>&1 || true; kubectl delete clusterrole opscontrol-provider-ci-node --ignore-not-found >/dev/null 2>&1 || true; kubectl delete namespace "$ns" --ignore-not-found --wait=false >/dev/null 2>&1 || true' EXIT
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
kubectl create clusterrole "$node_role" --verb=get --resource=nodes --resource-name="$node"
kubectl create clusterrolebinding "$node_role" --clusterrole="$node_role" --serviceaccount="$ns:monitoring-reader"
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
# SDK requests below use the actual read-only service account, not admin identity.
export OPSCONTROL_TEST_READER_TOKEN="$(kubectl -n "$ns" create token monitoring-reader --duration=10m)"
export OPSCONTROL_K8S_ALLOWED_NODES="$node"
python3 -m pip install 'kubernetes>=32,<37' --quiet
PYTHONPATH=backend OPSCONTROL_TEST_NAMESPACE="$ns" OPSCONTROL_TEST_POD="$pod" python3 - <<'PY'
import os
from kubernetes import client,config
from app.worker.provider_checks import kubernetes_health
configuration=client.Configuration()
config.load_kube_config(client_configuration=configuration)
configuration.cert_file=None
configuration.key_file=None
configuration.api_key={'authorization':'Bearer '+os.environ['OPSCONTROL_TEST_READER_TOKEN']}
configuration.api_key_prefix={}
configuration.refresh_api_key_hook=None
sdk=client.ApiClient(configuration)
from types import SimpleNamespace
reader=SimpleNamespace(CoreV1Api=lambda:client.CoreV1Api(sdk),AppsV1Api=lambda:client.AppsV1Api(sdk))
ns=os.environ["OPSCONTROL_TEST_NAMESPACE"]
pod=os.environ["OPSCONTROL_TEST_POD"]
observed=kubernetes_health({"namespace":ns,"pod_name":pod},reader)
assert observed["outcome"]=="SUCCESS" and observed["ready"],observed
deployment=kubernetes_health({"namespace":ns,"deployment_name":"demo-web"},reader)
assert deployment["outcome"]=="SUCCESS" and deployment["available_replicas"]>=1,deployment
node=kubernetes_health({"namespace":ns,"node_name":os.environ["OPSCONTROL_K8S_ALLOWED_NODES"]},reader)
assert node["outcome"]=="SUCCESS" and node["node_ready"],node
from kubernetes.client.exceptions import ApiException
for operation in [lambda:reader.CoreV1Api().list_namespaced_secret(ns),lambda:reader.CoreV1Api().list_node(),lambda:reader.CoreV1Api().list_namespaced_pod('default'),lambda:reader.CoreV1Api().delete_namespaced_pod(pod,ns)]:
    try:operation()
    except ApiException as error:assert error.status==403
    else:raise AssertionError('Read-only service account escaped provider boundaries')
print("REAL DISPOSABLE KUBERNETES POD, DEPLOYMENT AND APPROVED NODE PROVIDER ACCEPTANCE PASS")
PY
