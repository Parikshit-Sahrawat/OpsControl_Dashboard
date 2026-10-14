// UI affordances only. API dependencies and customer scope remain authoritative.
export const NAV_PERMISSIONS = {
  Overview: "overview.view",
  "Data Pipelines": "etl.view",
  "VM Health": "resources.view",
  APIs: "resources.view",
  Alerts: "alerts.view",
  Reports: "reports.view",
  "Resource Management": "customers.view",
  "Monitoring Setup": "collectors.view",
  "Access Management": "access.view",
};
export function hasPermission(user, key, customerId) {
  if (user?.platform_admin) return true;
  return customerId
    ? Boolean(user?.customer_permissions?.[customerId]?.includes(key))
    : Boolean(user?.permissions?.includes(key));
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
