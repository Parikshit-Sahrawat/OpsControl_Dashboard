const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    let message = "API request failed";
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

const qs = (params = {}) => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach(item => query.append(key, item));
    else query.set(key, value);
  }
  const text = query.toString();
  return text ? "?" + text : "";
};

export const fetchOrganizations = (params = {}) => request("/api/v1/organizations" + qs(params));
export const createOrganization = payload => request("/api/v1/organizations", { method: "POST", body: JSON.stringify(payload) });
export const updateOrganization = (id, payload) => request("/api/v1/organizations/" + id, { method: "PATCH", body: JSON.stringify(payload) });
export const disableOrganization = id => request("/api/v1/organizations/" + id, { method: "DELETE" });

export const fetchDataSources = (params = {}) => request("/api/v1/monitoring/data-sources" + qs(params));
export const createDataSource = payload => request("/api/v1/monitoring/data-sources", { method: "POST", body: JSON.stringify(payload) });
export const updateDataSource = (id, payload) => request("/api/v1/monitoring/data-sources/" + id, { method: "PATCH", body: JSON.stringify(payload) });
export const disableDataSource = id => request("/api/v1/monitoring/data-sources/" + id, { method: "DELETE" });

export const fetchCollectors = (params = {}) => request("/api/v1/monitoring/collectors" + qs(params));
export const createCollector = payload => request("/api/v1/monitoring/collectors", { method: "POST", body: JSON.stringify(payload) });
export const updateCollector = (id, payload) => request("/api/v1/monitoring/collectors/" + id, { method: "PATCH", body: JSON.stringify(payload) });
export const disableCollector = id => request("/api/v1/monitoring/collectors/" + id, { method: "DELETE" });

export const fetchMonitoringTemplates = (params = {}) => request("/api/v1/monitoring/templates" + qs(params));
export const createMonitoringTemplate = payload => request("/api/v1/monitoring/templates", { method: "POST", body: JSON.stringify(payload) });
export const updateMonitoringTemplate = (id, payload) => request("/api/v1/monitoring/templates/" + id, { method: "PATCH", body: JSON.stringify(payload) });
export const fetchMonitoringTemplateVersions = id => request("/api/v1/monitoring/templates/" + id + "/versions");
export const disableMonitoringTemplate = id => request("/api/v1/monitoring/templates/" + id, { method: "DELETE" });

export const fetchDataSourceTemplates = id => request("/api/v1/monitoring/data-sources/" + id + "/templates");
export const attachDataSourceTemplate = (id, payload) => request("/api/v1/monitoring/data-sources/" + id + "/templates", { method: "POST", body: JSON.stringify(payload) });
export const updateDataSourceTemplate = (id, templateId, payload) => request("/api/v1/monitoring/data-sources/" + id + "/templates/" + templateId, { method: "PATCH", body: JSON.stringify(payload) });
export const detachDataSourceTemplate = (id, templateId) => request("/api/v1/monitoring/data-sources/" + id + "/templates/" + templateId, { method: "DELETE" });
export const fetchEffectiveDataSourceConfiguration = id => request("/api/v1/monitoring/data-sources/" + id + "/effective-configuration");
