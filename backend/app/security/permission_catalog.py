"""Implemented actions only; catalog changes are reviewed code/migrations, not user input."""

import uuid

PROVIDER_ID = uuid.uuid5(uuid.NAMESPACE_URL, "opscontrol:default-service-provider")
PERMISSIONS = {
    "overview.view": "View operational overview",
    "customers.view": "View granted customer records",
    "customers.create": "Create customer records (no automatic access grant)",
    "customers.update": "Update/deactivate granted customers",
    "resources.view": "View customer resources",
    "resources.create": "Create customer resources",
    "resources.update": "Update customer resources",
    "resources.delete": "Deactivate customer resources",
    "etl.view": "View ETL executions and evidence",
    "etl.configure": "Configure customer ETL definitions",
    "etl.investigate": "Manage ETL investigations (not execute/restart jobs)",
    "alerts.view": "View monitoring alert evidence",
    "alerts.acknowledge": "Acknowledge monitoring alerts",
    "templates.view": "View policies",
    "templates.manage": "Manage customer policies (shared global catalog remains break-glass controlled)",
    "collectors.view": "View collector configuration/history",
    "collectors.manage": "Configure supported collectors (local execution requires break-glass approval)",
    "logs.view": "View granted logs",
    "logs.manage": "Configure customer log sources/evidence",
    "reports.view": "View customer operational reports/history",
    "access.view": "View internal access administration",
    "access.manage_users": "Manage provider employees and department memberships",
    "access.manage_departments": "Manage provider departments",
    "access.manage_roles": "Configure/assign delegable roles",
    "access.manage_permissions": "Configure customer access and permission overrides",
    "audit.view": "View provider access/security audit",
}
READ = frozenset(
    k
    for k in PERMISSIONS
    if k.endswith(".view") and not k.startswith("access.") and k != "audit.view"
)
LEGACY_ADMIN = READ | {
    "customers.update",
    "resources.create",
    "resources.update",
    "resources.delete",
    "etl.configure",
    "etl.investigate",
    "alerts.acknowledge",
    "templates.manage",
    "collectors.manage",
    "logs.manage",
}
LEGACY_OPERATOR = READ | {
    "etl.investigate",
    "alerts.acknowledge",
}
ROLE_SPECS = {
    "platform-administrator": ("Platform Administrator", set(PERMISSIONS)),
    "access-administrator": (
        "Access Administrator",
        {k for k in PERMISSIONS if k.startswith("access.")} | {"audit.view"},
    ),
    "resource-administrator": (
        "Resource Administrator",
        set(LEGACY_ADMIN) | {"customers.create"},
    ),
    "noc-operator": (
        "NOC Operator",
        set(READ) | {"etl.investigate", "alerts.acknowledge"},
    ),
    "incident-operator": (
        "Alert Operator",
        set(READ) | {"alerts.acknowledge"},
    ),
    "read-only-viewer": ("Read-Only Viewer", set(READ)),
    "legacy-customer-administrator": (
        "Legacy Customer Administrator",
        set(LEGACY_ADMIN),
    ),
    "legacy-customer-operator": ("Legacy Customer Operator", set(LEGACY_OPERATOR)),
}
LEGACY_ROLES = {
    "viewer": "read-only-viewer",
    "operator": "legacy-customer-operator",
    "org_admin": "legacy-customer-administrator",
}


def role_id(code):
    return uuid.uuid5(uuid.NAMESPACE_URL, "opscontrol:role:" + code)


def delegable(key):
    return key in PERMISSIONS and not key.startswith("access.") and key != "audit.view"
