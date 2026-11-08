"""Explicit, versioned host method applicability; unknown contracts fail closed."""

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from fastapi import HTTPException
from app.telemetry.configuration import MethodInput, validate_method, host_os


class APIMethod(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=160)
    method_type: Literal["HTTPS"]
    configuration: dict


class APIApplicability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    family: Literal["API"]
    source_types: list[Literal["HTTP", "HTTPS", "API", "API_ENDPOINT"]] = Field(
        min_length=1
    )
    methods: list[APIMethod] = Field(min_length=1, max_length=1)
    collector_override_fields: list[Literal["interval_seconds", "interval"]] = Field(
        default_factory=list
    )
    override_components: list[Literal["attributes", "metrics", "alerts", "logs"]] = (
        Field(default_factory=list)
    )


def parse_applicability(value):
    if not isinstance(value, dict):
        raise ValueError("Applicability manifest must be an object")
    if type(value.get("schema_version")) is not int:
        raise ValueError("Applicability schema_version must be an integer")
    return (
        APIApplicability if value.get("family") == "API" else Applicability
    ).model_validate(value)


class Applicability(BaseModel):
    model_config = ConfigDict(extra="forbid")
    family: Literal["HOST"] = "HOST"
    schema_version: Literal[1]
    source_types: list[
        Literal["LINUX", "LINUX_HOST", "WINDOWS", "WINDOWS_HOST", "VM"]
    ] = Field(min_length=1, max_length=5)
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
        contract = parse_applicability(manifest)
        if isinstance(contract, APIApplicability):
            from app.services.api_monitoring_config import validate_api_settings

            if source.source_type not in contract.source_types or package.get(
                "collector", {}
            ).get("type") not in (None, "HTTP", "API"):
                reasons.append(
                    dict(code="SOURCE_METHOD_INCOMPATIBLE", path="applicability")
                )
            method = contract.methods[0]
            if set(method.configuration) - {
                "url",
                "method",
                "expected_status",
                "timeout_seconds",
                "headers",
                "max_response_time_ms",
            }:
                reasons.append(
                    dict(code="METHOD_SCHEMA_INVALID", path="applicability/methods")
                )
            validate_api_settings(
                {**package.get("collector", {}), **method.configuration}, source
            )
            # This is shape/HTTPS compatibility only. Real worker allowlists,
            # DNS/TLS/connectivity are still mandatory at preview/apply/dispatch.
        else:
            os_type = host_os(source)
            expected_os = {
                "LINUX": "Linux",
                "LINUX_HOST": "Linux",
                "WINDOWS": "Windows",
                "WINDOWS_HOST": "Windows",
            }.get(source.source_type)
            if expected_os is not None and os_type != expected_os:
                reasons.append(
                    dict(code="SOURCE_OS_IDENTITY_CONFLICT", path="applicability/os")
                )
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
                reasons.append(
                    dict(code="OS_SOURCE_INCOMPATIBLE", path="applicability")
                )
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
    except (ValueError, HTTPException):
        reasons.append(
            dict(
                code="METHOD_SCHEMA_INVALID_OR_UNVERIFIED", path="applicability/methods"
            )
        )
    return reasons
