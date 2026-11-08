"""Explicit, versioned host method applicability; unknown contracts fail closed."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from app.telemetry.configuration import MethodInput, validate_method, host_os


class Applicability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    source_types: list[str] = Field(min_length=1, max_length=30)
    os: list[Literal["Windows", "Linux"]] = Field(min_length=1, max_length=2)
    methods: list[MethodInput] = Field(min_length=1, max_length=30)
    collector_override_fields: list[Literal["interval_seconds", "interval"]] = Field(
        default_factory=list
    )
    override_components: list[Literal["attributes", "metrics", "alerts", "logs"]] = (
        Field(default_factory=list)
    )


def applicability(source, package, overrides):
    manifest = package.get("applicability")
    if manifest is None:
        return [dict(code="LEGACY_APPLICABILITY_UNVERIFIED", path="applicability")]
    reasons = []
    try:
        contract = Applicability.model_validate(manifest)
        os_type = host_os(source)
        if package.get("collector", {}).get("type") not in (
            None,
            "OTEL",
            "WINDOWS",
            "LINUX",
        ):
            reasons.append(
                dict(code="COLLECTOR_METHOD_INCOMPATIBLE", path="collector/type")
            )
        if (
            source.source_type not in contract.source_types
            or os_type not in contract.os
        ):
            reasons.append(dict(code="OS_SOURCE_INCOMPATIBLE", path="applicability"))
        for method in contract.methods:
            validate_method(method, os_type)
        allowed = set(contract.override_components)
        if contract.collector_override_fields:
            allowed.add("collector")
        collector_overrides = (overrides or {}).get("collector", {})
        if set(collector_overrides) - set(contract.collector_override_fields) or any(
            not isinstance(v, int) or isinstance(v, bool) or not 5 <= v <= 86400
            for v in collector_overrides.values()
        ):
            reasons.append(
                dict(code="OVERRIDE_PATH_FORBIDDEN", path="overrides/collector")
            )
        if set(overrides or {}) - allowed:
            reasons.append(dict(code="OVERRIDE_PATH_FORBIDDEN", path="overrides"))
    except ValueError:
        reasons.append(
            dict(
                code="METHOD_SCHEMA_INVALID_OR_UNVERIFIED", path="applicability/methods"
            )
        )
    return reasons
