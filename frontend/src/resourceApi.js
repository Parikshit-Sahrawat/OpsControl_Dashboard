import { authHeaders } from "./auth";
import { readAllPages } from "./pagination";
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(API_BASE + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options.headers || {}),
    },
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
    if (Array.isArray(value)) value.forEach((item) => query.append(key, item));
    else query.set(key, value);
  }
  const text = query.toString();
  return text ? "?" + text : "";
};

const completeList = (path, params) => {
  const headers = authHeaders();
  const scope = JSON.stringify(headers);
  return readAllPages(
    (offset) =>
      request(path + qs({ ...params, paginated: true, limit: 200, offset }), {
        headers,
      }),
    () => JSON.stringify(authHeaders()) === scope,
  );
};
export const fetchOrganizations = (params = {}) =>
  completeList("/api/v1/organizations", params);
export const createOrganization = (payload) =>
  request("/api/v1/organizations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateOrganization = (id, payload) =>
  request("/api/v1/organizations/" + id, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const disableOrganization = (id) =>
  request("/api/v1/organizations/" + id, { method: "DELETE" });

export const fetchDataSources = (params = {}) =>
  completeList("/api/v1/resource-management/data-sources", params);
export const createDataSource = (payload) =>
  request("/api/v1/resource-management/data-sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateDataSource = (id, payload) =>
  request("/api/v1/resource-management/data-sources/" + id, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const disableDataSource = (id) =>
  request("/api/v1/resource-management/data-sources/" + id, {
    method: "DELETE",
  });

export const fetchCollectors = async (params = {}) => {
  const ids = params.data_source_id;
  if (!Array.isArray(ids) || ids.length <= 50) {
    return completeList("/api/v1/resource-management/collectors", params);
  }
  // Keep each request line below common ingress limits. Use bounded sequential
  // batches rather than a burst proportional to the complete resource list.
  const rows = [];
  for (let offset = 0; offset < ids.length; offset += 50) {
    rows.push(
      ...(await completeList("/api/v1/resource-management/collectors", {
        ...params,
        data_source_id: ids.slice(offset, offset + 50),
      })),
    );
  }
  return rows;
};
export const createCollector = (payload) =>
  request("/api/v1/resource-management/collectors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateCollector = (id, payload) =>
  request("/api/v1/resource-management/collectors/" + id, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const disableCollector = (id) =>
  request("/api/v1/resource-management/collectors/" + id, { method: "DELETE" });

export const fetchMonitoringTemplates = (params = {}) =>
  request("/api/v1/monitoring/templates" + qs(params));
export const createMonitoringTemplate = (payload) =>
  request("/api/v1/monitoring/templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateMonitoringTemplate = (id, payload) =>
  request("/api/v1/monitoring/templates/" + id, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const fetchMonitoringTemplateVersions = (id) =>
  request("/api/v1/monitoring/templates/" + id + "/versions");
export const disableMonitoringTemplate = (id) =>
  request("/api/v1/monitoring/templates/" + id, { method: "DELETE" });

export const fetchDataSourceTemplates = (id) =>
  request("/api/v1/monitoring/data-sources/" + id + "/templates");
export const attachDataSourceTemplate = (id, payload) =>
  request("/api/v1/monitoring/data-sources/" + id + "/templates", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateDataSourceTemplate = (id, templateId, payload) =>
  request(
    "/api/v1/monitoring/data-sources/" + id + "/templates/" + templateId,
    { method: "PATCH", body: JSON.stringify(payload) },
  );
export const detachDataSourceTemplate = (id, templateId) =>
  request(
    "/api/v1/monitoring/data-sources/" + id + "/templates/" + templateId,
    { method: "DELETE" },
  );
export const fetchEffectiveDataSourceConfiguration = (id) =>
  request("/api/v1/monitoring/data-sources/" + id + "/effective-configuration");
