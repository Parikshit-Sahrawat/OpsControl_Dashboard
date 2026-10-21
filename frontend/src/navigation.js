import { canNavigate, hasPermission } from "./permissions.js";

// Only existing sections have addressable child hashes. Unknown or unauthorized
// hashes never become a source of authorization or a new page identity.
export const SECTION_ROUTES = {
  "#/resources/organizations": ["Resource Management", "organizations"],
  "#/resources/data-resources": ["Resource Management", "resources"],
  "#/resources/collectors": ["Resource Management", "collectors"],
  "#/resources/event-parameters": ["Resource Management", "parameters"],
  "#/resources/alert-rules": ["Resource Management", "rules"],
  "#/resources/notification-delivery": ["Resource Management", "delivery"],
  "#/access/employees": ["Access Management", "Employees"],
  "#/access/departments": ["Access Management", "Departments"],
  "#/access/roles": ["Access Management", "Roles & Permissions"],
  "#/access/organisational-access": ["Access Management", "Organisational Access"],
  "#/access/audit": ["Access Management", "Access Audit"],
};

export function canOpenSection(user, page, section) {
  if (!canNavigate(user, page)) return false;
  if (page === "Resource Management") {
    if (section === "organizations") return hasPermission(user, "customers.view");
    if (section === "collectors")
      return hasPermission(user, "collectors.view") && hasPermission(user, "resources.view");
    if (section === "delivery") return hasPermission(user, "templates.view");
    if (["parameters", "rules"].includes(section))
      return hasPermission(user, "templates.view") && hasPermission(user, "resources.view");
    return section === "resources" && (hasPermission(user, "resources.view") || hasPermission(user, "resources.create"));
  }
  if (page === "Access Management")
    return section === "Access Audit"
      ? hasPermission(user, "audit.view")
      : ["Employees", "Departments", "Roles & Permissions", "Organisational Access"].includes(section);
  return false;
}

export function readSectionRoute(hash, user) {
  const route = SECTION_ROUTES[hash];
  return route && canOpenSection(user, ...route) ? route : null;
}

export function sectionHash(page, section) {
  return Object.entries(SECTION_ROUTES).find(([, route]) => route[0] === page && route[1] === section)?.[0] || "";
}
