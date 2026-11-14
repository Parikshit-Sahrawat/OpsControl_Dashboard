import { canNavigate } from "./permissions.js";
import { canOpenSection } from "./navigation.js";

// Labels describe the UI; keys remain the existing page identities and guards.
export const FOUNDATION_SECTIONS = [
  { name: "Overview", items: [["Overview", "Dashboard"]] },
  { name: "Operations", items: [
    ["Data Pipeline Monitoring", "Data Pipeline Monitoring"],
    ["Compute Health", "Compute Instances"],
    ["API Endpoint Monitoring", "API Endpoints"],
    ["Alerts", "Alerts"], ["Reports", "Reports"],
  ] },
  { name: "Resource Management", items: [
    ["Resource Management", "Organizations", "organizations"],
    ["Resource Management", "Compute Instances", "compute-instances"],
    ["Resource Management", "Data Pipelines", "data-pipelines"],
    ["Resource Management", "APIs", "apis"],
    ["Resource Management", "Collectors", "collectors"],
    ["Resource Management", "Event Parameters", "parameters"],
    ["Resource Management", "Alert Rules", "rules"],
    ["Resource Management", "Notification Delivery", "delivery"],
  ] },
  { name: "Access Management", items: [
    ["Access Management", "Departments", "Departments"],
    ["Access Management", "Employees", "Employees"],
    ["Access Management", "Roles & Permissions", "Roles & Permissions"],
    ["Access Management", "Organisational Access", "Organisational Access"],
    ["Access Management", "Access Audit", "Access Audit"],
  ] },
];

export function visibleFoundationSections(user) {
  return FOUNDATION_SECTIONS.map(section => ({ ...section, items: section.items.filter(([page, , child]) =>
    child ? canOpenSection(user, page, child) : canNavigate(user, page)) })).filter(section => section.items.length);
}
