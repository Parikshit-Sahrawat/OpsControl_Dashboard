import { canNavigate } from './permissions.js';
import { canOpenSection } from './navigation.js';

// Existing destinations only: directory presentation never grants authority.
export const FEATURE_GROUPS = [
  { name: 'Overview', items: [['Overview', 'Dashboard']] },
  { name: 'Operations', items: [
    ['Data Pipeline Monitoring', 'Data Pipelines'], ['Compute Health', 'Compute Instances'],
    ['API Endpoint Monitoring', 'API Endpoints'], ['Alerts', 'Alerts'], ['Reports', 'Reports'],
  ] },
  { name: 'Resource Management', items: [
    ['Resource Management', 'Organizations', 'organizations'],
    ['Resource Management', 'Data Sources / Resources', 'resources'],
    ['Resource Management', 'Collectors', 'collectors'],
    ['Resource Management', 'Monitoring Templates', 'templates'],
    ['Resource Management', 'Event Parameters', 'parameters'],
    ['Resource Management', 'Alert Rules', 'rules'],
    ['Resource Management', 'Notification Delivery', 'delivery'],
  ] },
  { name: 'Access Management', items: [
    ['Access Management', 'Departments', 'Departments'], ['Access Management', 'Employees', 'Employees'],
    ['Access Management', 'Roles & Permissions', 'Roles & Permissions'],
    ['Access Management', 'Organisational Access', 'Organisational Access'],
    ['Access Management', 'Access Audit', 'Access Audit'],
  ] },
];
export function visibleFeatureGroups(user) {
  return FEATURE_GROUPS.map(group => ({...group, items: group.items.filter(([page,,section]) =>
    section ? canOpenSection(user, page, section) : canNavigate(user, page))})).filter(group => group.items.length);
}
