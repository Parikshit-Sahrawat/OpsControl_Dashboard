// Hydrate only editable, non-secret settings from the authorized active collector.
export const defaultMonitoringSettings = () => ({
  url: "", method: "GET", status: "200", timeout: "8", latency: "", header: "",
  workerId: "", rules: [], includeTemplates: false,
});

export async function readMonitoringSettings(request, sourceId) {
  const activation = await request(`/api/v1/data-sources/${sourceId}/activation`);
  const defaults = defaultMonitoringSettings();
  if (activation.status !== "ACTIVE" || !activation.collector_id) return defaults;
  const collector = await request(`/api/v1/monitoring/collectors/${activation.collector_id}`);
  if (collector.data_source_id !== sourceId) throw Error("Collector does not belong to the selected Data Source");
  if (!collector.enabled) return defaults;
  const config = collector.configuration || {};
  return {
    url: typeof config.url === "string" ? config.url : "",
    method: config.method === "HEAD" ? "HEAD" : "GET",
    status: String(config.expected_status ?? 200), timeout: String(config.timeout_seconds ?? 8),
    latency: config.max_response_time_ms == null ? "" : String(config.max_response_time_ms),
    header: typeof config.headers?.["x-opscontrol-check"] === "string" ? config.headers["x-opscontrol-check"] : "",
    workerId: collector.remote_worker_id || "",
    rules: activation.rule_version_ids || [], includeTemplates: activation.include_templates === true,
  };
}

// Tickets cover both resource changes and edits made while a fetch is pending.
export function createHydrationGuard() {
  let generation = 0, revision = 0;
  return {
    begin() { generation++; revision = 0; return [generation, revision]; },
    ticket() { return [generation, revision]; },
    edit() { revision++; },
    invalidate() { generation++; },
    current([g, r]) { return generation === g && revision === r; },
    sameSource([g]) { return generation === g; },
  };
}

export function hydrateMonitoringSettings(request, sourceId, guard, apply, ready, fail) {
  const ticket = guard.begin();
  apply(defaultMonitoringSettings());
  if (sourceId) readMonitoringSettings(request, sourceId).then(settings => {
    if (guard.current(ticket)) apply(settings);
    if (guard.sameSource(ticket)) ready();
  }).catch(error => { if (guard.sameSource(ticket)) fail(error); });
  return () => guard.invalidate();
}
