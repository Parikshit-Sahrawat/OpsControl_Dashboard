// UI affordances only. API dependencies and customer scope remain authoritative.
export const NAV_PERMISSIONS = {
  Overview: "overview.view",
  "Data Pipeline Monitoring": "etl.view",
  "Compute Health": "resources.view",
  "API Endpoint Monitoring": "resources.view",
  Alerts: "alerts.view",
  Incidents: "incidents.view",
  Reports: "reports.view",
  "Resource Management": "customers.view",
  "Access Management": "access.view",
};
export function hasPermission(user, key, customerId, resource) {
  if (user?.platform_admin) return true;
  const granted = customerId
    ? Boolean(user?.customer_permissions?.[customerId]?.includes(key))
    : Boolean(user?.permissions?.includes(key));
  if (!granted || !resource) return granted;
  const rows = (user.access_boundaries || []).filter(
    (b) =>
      ["LIMIT", "DENY"].includes(b.kind) &&
      b.specification.customers.includes(customerId) &&
      b.specification.permissions.includes(key),
  );
  const matches = (b) =>
    (!b.specification.environments.length ||
      b.specification.environments.includes(resource.environment)) &&
    (!b.specification.resources.length ||
      b.specification.resources.includes(resource.id));
  const limits = rows.filter((b) => b.kind === "LIMIT");
  return (
    (!limits.length || limits.every(matches)) &&
    !rows.some((b) => b.kind === "DENY" && matches(b))
  );
}

export function canNavigate(user, page) {
  if (page === "Resource Management")
    return ["customers.view", "customers.create", "resources.view"].some(
      (key) => hasPermission(user, key),
    );
  return Boolean(
    NAV_PERMISSIONS[page] && hasPermission(user, NAV_PERMISSIONS[page]),
  );
}
export const administrationPage = (page) =>
  ["Resource Management", "Access Management"].includes(page);

// Local preferences are untrusted. Only arrays of string IDs can enter selector
// state; authenticated customer discovery filters them before operational reads.
export function parseCustomerSelection(raw) {
  try {
    const value = JSON.parse(raw || "[]");
    return Array.isArray(value)
      ? [...new Set(value.filter((id) => typeof id === "string"))]
      : [];
  } catch {
    return [];
  }
}
