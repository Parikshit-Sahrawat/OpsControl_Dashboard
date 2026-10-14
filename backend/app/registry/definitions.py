"""Derive rendering and validation from the same authoritative typed schemas."""

import hashlib, json
from app.unified.schemas import (
    VMCreate,
    ETLCreate,
    APICreate,
    VMParameters,
    ETLParameters,
    APIParameters,
)
from app.unified.api import NativeAlertSetup
from app.telemetry.rules import DestinationInput
from app.telemetry.configuration import METHOD_SCHEMAS

LABELS = {
    "VM": "Compute Instance",
    "ETL": "Data Pipeline",
    "API": "API Endpoint",
    "HOST_METRICS": "Host Metrics",
    "SERVICES": "Services",
    "SYSLOG_RECEIVER": "Syslog",
    "FILE_LOG": "File Logs",
    "METRIC_SCRAPE": "OpsControl Scrape",
    "OTLP_RECEIVER": "OTLP Transport",
}


def render_definition(key, schema):
    fields = []
    for name, value in schema.get("properties", {}).items():
        nullable = value.get("anyOf", [])
        values = value.get("enum") or next(
            (v.get("enum") for v in nullable if v.get("enum")), None
        )
        kind = (
            value.get("type")
            or next((v.get("type") for v in nullable if v.get("type") != "null"), None)
            or ("object" if "$ref" in value else "string")
        )
        secret = name.endswith("_ref")
        fields.append(
            {
                "key": name,
                "label": value.get("title") or name.replace("_", " ").capitalize(),
                "description": value.get("description", ""),
                "input_type": (
                    "select"
                    if values
                    else {
                        "boolean": "checkbox",
                        "integer": "number",
                        "number": "number",
                        "object": "json",
                        "array": "json",
                    }.get(kind, "text")
                ),
                "data_type": kind,
                "default": value.get("default"),
                "required": name in schema.get("required", []),
                "allowed_values": values or [],
                "validation": {
                    k: v
                    for k, v in value.items()
                    if k
                    in {
                        "minimum",
                        "maximum",
                        "minLength",
                        "maxLength",
                        "pattern",
                        "minItems",
                        "maxItems",
                    }
                },
                "conditional_requirements": (
                    {"protocol": "HTTPS"}
                    if name == "credential_ref" and key == "API"
                    else {}
                ),
                "os_capabilities": (
                    ["Linux", "Windows"]
                    if key not in {"SYSLOG_RECEIVER"}
                    else ["Linux", "Windows"]
                ),
                "platform_capabilities": [],
                "inheritance": (
                    "VM"
                    if key == "ETL" and name in {"organization_id", "environment"}
                    else None
                ),
                "override_policy": (
                    "READ_ONLY_INHERITED"
                    if key == "ETL" and name in {"organization_id", "environment"}
                    else "CONFIGURABLE"
                ),
                "secret_handling": "REFERENCE_ONLY" if secret else "NONE",
            }
        )
    return {"label": LABELS.get(key, key), "fields": fields, "json_schema": schema}


def package():
    definitions = {
        key: render_definition(key, model.model_json_schema())
        for key, model in {
            "VM": VMCreate,
            "ETL": ETLCreate,
            "API": APICreate,
            "PARAM_VM": VMParameters,
            "PARAM_ETL": ETLParameters,
            "PARAM_API": APIParameters,
            "ALERT_SETUP": NativeAlertSetup,
            "NOTIFICATION_DELIVERY": DestinationInput,
            **METHOD_SCHEMAS,
        }.items()
    }
    for field in definitions["FILE_LOG"]["fields"]:
        if field["key"] == "source":
            field["value_capabilities"] = {
                "JOURNALD": {"os": ["Linux"]},
                "WINDOWS_EVENT": {"os": ["Windows"]},
            }
        elif field["key"] == "channel":
            field["visible_if"] = {"source": ["WINDOWS_EVENT"]}
            field["os_capabilities"] = ["Windows"]
        elif field["key"] in {
            "paths",
            "exclusions",
            "format",
            "multiline_pattern",
            "start_at",
        }:
            field["visible_if"] = {"source": ["FILE"]}
            if field["key"] == "paths":
                field["required_when"] = {"source": ["FILE"]}
    platforms = {}
    try:
        from app.pipeline_adapters import ADAPTER_DEFINITIONS, CONFIG_SCHEMAS

        for key, spec in ADAPTER_DEFINITIONS.items():
            platforms[key] = {k: v for k, v in spec.items() if k != "json_schema"}
            attrs = CONFIG_SCHEMAS.get(key, {}).get("attributes", [])
            schema = {
                "type": "object",
                "additionalProperties": False,
                "required": [a["key"] for a in attrs if a.get("required")],
                "properties": {
                    a["key"]: {
                        "type": a.get("type", "string"),
                        "title": a.get("label"),
                        "description": a.get("description", ""),
                        **(
                            {"items": {"type": "string"}}
                            if a.get("type") == "array"
                            else {}
                        ),
                    }
                    for a in attrs
                },
            }
            definitions["PLATFORM_" + key] = render_definition(
                "PLATFORM_" + key, schema
            )
    except ImportError:
        pass  # No external connection or fabricated capability is attempted.
    capabilities = {
        "os": {
            "Linux": {"agent": True, "services": "systemd", "native_logs": "Journald"},
            "Windows": {
                "agent": True,
                "services": "SCM",
                "native_logs": "Windows Event Log",
            },
            "Other": {"agent": False, "reason": "Unsupported host-agent OS"},
        },
        "platforms": platforms,
        "methods": {
            key: {
                "label": LABELS.get(key, key),
                "signals": (
                    ["logs"]
                    if key in {"FILE_LOG", "SYSLOG_RECEIVER"}
                    else (
                        ["metrics"]
                        if key != "OTLP_RECEIVER"
                        else ["logs", "metrics", "traces"]
                    )
                ),
                "concurrent": True,
            }
            for key in METHOD_SCHEMAS
        },
    }
    payload = {"definitions": definitions, "capabilities": capabilities}
    return {
        **payload,
        "sha256": hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, default=str, separators=(",", ":")
            ).encode()
        ).hexdigest(),
    }
