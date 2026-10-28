"""Removed provider identifiers; retained solely for rejection of legacy input."""
import re


def is_excluded_platform(value):
    if not isinstance(value, str):
        return False
    words = set(re.split(r"[^a-z0-9]+", value.lower()))
    return bool(words & {"kubernetes", "k8s", "eks", "aks", "gke", "openshift"})
