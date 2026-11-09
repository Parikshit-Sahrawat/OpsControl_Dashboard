export const ENVIRONMENTS = ["PROD", "QA", "TEST", "DEV", "SANDBOX"];
export function readResourceFilters(search) {
  const q = new URLSearchParams(search);
  return { domain: q.get("rm.domain") || "VM", customer: (q.get("rm.customer") || "").slice(0, 64), environment: (q.get("rm.environment") || "").slice(0, 20), search: (q.get("rm.search") || "").slice(0, 200), active: q.get("rm.active") || "" };
}
export function writeResourceFilters(search, filters) {
  const q = new URLSearchParams(search);
  for (const [field, value] of Object.entries(filters)) {
    if (!["customer", "environment", "search", "active", "domain"].includes(field)) continue;
    if (value) q.set("rm." + field, value); else q.delete("rm." + field);
  }
  return q.toString();
}
export function validateResourceFilters(filters, customers) {
  if (filters.domain && !["VM", "API", "ETL"].includes(filters.domain)) return "Select a supported resource type or reset filters.";
  if (filters.customer && !customers.some(c => c.id === filters.customer)) return "The bookmarked customer is unavailable in your authorized inventory. Reset filters or select an authorized customer.";
  if (filters.environment && !ENVIRONMENTS.includes(filters.environment)) return "Select a supported environment or reset filters.";
  if (!["", "true", "false"].includes(filters.active)) return "Select a supported configuration state or reset filters.";
  return "";
}
export function configurationCapable(user, customerIds = []) {
  if (user?.platform_admin) return true;
  const keys = ["resources.create", "resources.update", "collectors.manage", "templates.manage", "access.manage"];
  return keys.some(key => customerIds.length ? customerIds.some(id => user?.customer_permissions?.[id]?.includes(key)) : user?.permissions?.includes(key));
}
