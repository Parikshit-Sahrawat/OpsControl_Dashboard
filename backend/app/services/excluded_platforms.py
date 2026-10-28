"""Scope checks for operational configuration, never historical telemetry values."""
import re
from fastapi import HTTPException

_ALIASES = {"kubernetes", "k8s", "eks", "aks", "gke", "openshift", "k3s", "k0s",
            "microk8s", "rke", "rke2", "amazonelasticcontainerserviceforkubernetes",
            "amazonelastickubernetesservice", "azurekubernetesservice", "googlekubernetesengine"}
_IDENTITIES = {"type", "provider", "platform", "sourcetype", "collectortype", "resourcetype", "extract", "receiver"}

def is_excluded_platform(value):
    if not isinstance(value, str):
        return False
    words = set(re.split(r"[^a-z0-9]+", value.lower()))
    compact = re.sub(r"[^a-z0-9]", "", value.lower())
    return bool(words & _ALIASES) or compact in _ALIASES or "kubernetes" in compact or "openshift" in compact

def require_supported_configuration(value):
    """Reject operational identities at any depth; generic labels are not adapters."""
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = re.sub(r"[^a-z0-9]", "", str(key).lower())
            if normalized in {"kubeconfig", "kubectl", "helm"} or is_excluded_platform(key):
                raise ValueError("Excluded container orchestration configuration")
            if normalized in _IDENTITIES and is_excluded_platform(item):
                raise ValueError("Excluded container orchestration platform")
            # Attribute names/values are telemetry labels, not executable providers.
            if normalized not in {"attributes", "customattributes", "tags"}:
                require_supported_configuration(item)
    elif isinstance(value, list):
        for item in value:
            require_supported_configuration(item)
    return value

def require_supported_source(source):
    if source is None:
        raise HTTPException(404, "Data source not found")
    if is_excluded_platform(source.source_type):
        raise HTTPException(422, "Container orchestration platforms are excluded from product scope")
    try:
        require_supported_configuration(getattr(source, "connection_config", None))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None

def require_supported_collector(collector, source):
    require_supported_source(source)
    if is_excluded_platform(collector.collector_type):
        raise HTTPException(422, "Container orchestration collectors are excluded from product scope")
    try:
        require_supported_configuration(collector.configuration)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
