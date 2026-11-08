"""Configuration guards; never evidence of telemetry or operational health."""

from fastapi import HTTPException


def require_enabled_parent(source, enabled):
    if enabled is True and not source.enabled:
        raise HTTPException(409, "Cannot enable a collector on a disabled data source")
