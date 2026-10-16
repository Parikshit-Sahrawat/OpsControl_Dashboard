"""Native pipeline adapter registry. Live acceptance is recorded separately."""

from .core import Adapter, AdapterError, Batch
from .http import Airflow, IICS, NiFi, AzureDataFactory, Talend
from .native import Pentaho, AWSGlue, SSIS, CustomShell
from .pentaho_contracts import describe_pentaho_monitoring_contract

PLATFORM_ADAPTERS = {
    cls.platform: cls
    for cls in (
        Pentaho,
        IICS,
        Airflow,
        NiFi,
        AzureDataFactory,
        AWSGlue,
        SSIS,
        Talend,
        CustomShell,
    )
}
ADAPTER_DEFINITIONS = {
    name: {
        "required": list(cls.required),
        "fields": sorted(set(cls.fields + cls.required)),
        "capabilities": list(cls.capabilities),
        "read_only": True,
    }
    for name, cls in PLATFORM_ADAPTERS.items()
}

# Declarations are additive metadata; they never register a runnable adapter or
# expand accepted connection fields for unimplemented monitoring surfaces.
ADAPTER_DEFINITIONS["PENTAHO"][
    "monitoring_surface_contract"
] = describe_pentaho_monitoring_contract()

# Versioned form descriptors are shared by API validation and the UI registry.
CONFIG_SCHEMAS = {
    name: {
        "version": 1,
        "platform": name,
        "additional_properties": False,
        "attributes": [
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "type": (
                    "integer"
                    if key in {"timeout_seconds", "page_size", "max_bytes"}
                    else (
                        "array"
                        if key in {"allowed_hosts", "allowed_cidrs", "component_ids"}
                        else "string"
                    )
                ),
                "required": key in cls.required,
                "secret_reference": key in {"credential_ref", "connection_ref"},
                "override_policy": "CONFIGURED",
                "description": (
                    "Operator-managed secret reference; never plaintext"
                    if key.endswith("_ref")
                    else "Read-only " + name + " connector setting"
                ),
            }
            for key in sorted(set(cls.fields + cls.required))
        ],
    }
    for name, cls in PLATFORM_ADAPTERS.items()
}

for definition in CONFIG_SCHEMAS.values():
    for attribute in definition["attributes"]:
        key = attribute["key"]
        if key in {"page_size", "timeout_seconds", "max_bytes"}:
            attribute.update(
                default={"page_size": 100, "timeout_seconds": 20, "max_bytes": 1048576}[
                    key
                ],
                minimum=1,
                maximum={
                    "page_size": 1000,
                    "timeout_seconds": 60,
                    "max_bytes": 1048576,
                }[key],
            )
        if key == "credential_header":
            attribute.update(
                default="INFA-SESSION-ID",
                allowed_values=["Authorization", "INFA-SESSION-ID", "icSessionId"],
            )
        if key == "api_version":
            attribute["default"] = (
                "v1" if definition["platform"] == "AIRFLOW" else "2018-06-01"
            )
        if key == "collect_logs":
            attribute["default"] = False
        if key == "monitoring_context":
            attribute.update(
                type="object",
                description="Optional version-1 Pentaho observation scope; exact build is not certification",
            )

for definition in CONFIG_SCHEMAS.values():
    for attribute in definition["attributes"]:
        if attribute["key"] == "auth_type":
            attribute.update(
                default="BEARER", allowed_values=["BEARER", "BASIC", "NONE"]
            )

for definition in CONFIG_SCHEMAS.values():
    for attribute in definition["attributes"]:
        key = attribute["key"]
        if key == "include_steps":
            attribute.update(type="boolean", default=False)
        if key in {"step_call_budget", "step_page_size"}:
            attribute.update(
                type="integer",
                default=1 if key == "step_call_budget" else 100,
                minimum=1,
                maximum=4 if key == "step_call_budget" else 1000,
            )

for definition in CONFIG_SCHEMAS.values():
    for attribute in definition["attributes"]:
        if attribute["key"] == "collect_logs":
            attribute.update(type="boolean", default=False)


def describe_platform(platform):
    """Backend route helper: declared capability/schema only, no false remote discovery."""
    if platform not in PLATFORM_ADAPTERS:
        raise AdapterError("CONFIGURATION", "Unsupported pipeline platform")
    import copy

    description = {
        "platform": platform,
        "configuration_schema": copy.deepcopy(CONFIG_SCHEMAS[platform]),
        "capabilities": list(PLATFORM_ADAPTERS[platform].capabilities),
        "step_collection": PLATFORM_ADAPTERS[platform].step_semantics,
        "live_verified": False,
    }
    if platform == "PENTAHO":
        description["monitoring_surface_contract"] = (
            describe_pentaho_monitoring_contract()
        )
    return description


def validate_platform_configuration(platform, configuration):
    if platform not in PLATFORM_ADAPTERS:
        raise AdapterError("CONFIGURATION", "Unsupported pipeline platform")
    return PLATFORM_ADAPTERS[platform](configuration).config


def test_platform_connection(platform, configuration):
    """Perform actual provider reads. Call only behind customer and config-read authorization."""
    if platform not in PLATFORM_ADAPTERS:
        raise AdapterError("CONFIGURATION", "Unsupported pipeline platform")
    return PLATFORM_ADAPTERS[platform](configuration).test_connection()
