import { useEffect, useMemo, useState } from "react";
import "../resource-v2.css";
import {
  fetchOrganizations, createOrganization, updateOrganization, disableOrganization,
  fetchDataSources, createDataSource, updateDataSource, disableDataSource,
  fetchCollectors, createCollector, disableCollector,
  fetchMonitoringTemplates, createMonitoringTemplate, updateMonitoringTemplate,
  fetchMonitoringTemplateVersions, disableMonitoringTemplate,
  fetchDataSourceTemplates, attachDataSourceTemplate, updateDataSourceTemplate,
  detachDataSourceTemplate, fetchEffectiveDataSourceConfiguration,
} from "../resourceApi";

const NAV = [
  ["organizations", "Organizations", "Customer boundaries"],
  ["data-sources", "Data Sources", "Customer machines and workloads"],
  ["collectors", "Collectors", "Installed agents and telemetry"],
  ["templates", "Templates", "Reusable monitoring policy packages"],
];
const ENVIRONMENTS = ["PROD", "QA", "TEST", "DEV", "SANDBOX"];
const OS_TYPES = ["Windows", "Linux"];
const ROLES = ["Application", "ETL", "Database", "Web", "API", "File Transfer", "Batch", "Other"];
const PRODUCTS = ["SPM", "SPP", "Other"];
const HOST_GROUPS = ["PROD", "QA", "TEST", "DEV", "SANDBOX", "SLM", "SPM", "SPP", "Windows Servers", "Linux Servers", "Application Servers", "Database Servers", "ETL Servers"];
const TELEMETRY = ["VM metrics", "System logs", "Application logs", "ETL logs", "Services", "Traces"];
const ATTR_TYPES = ["TEXT", "NUMBER", "BOOLEAN", "SELECT", "MULTI_SELECT", "PASSWORD", "PATH", "DIRECTORY", "FILE", "IP_ADDRESS", "PORT", "URL", "DURATION", "REGEX", "TIME"];
const VALUE_SOURCES = ["DATA_SOURCE", "DEFAULT", "DISCOVERY", "EXPRESSION", "SECRET"];
const METRIC_METHODS = ["HOST_METRIC", "FILESYSTEM", "PROCESS", "SERVICE", "HTTP", "SQL", "ETL_EXECUTION", "CUSTOM_QUERY"];
const AGGREGATIONS = ["avg", "min", "max", "sum", "count", "rate", "p95", "p99"];
const ALERT_DOMAINS = ["VM", "Application / Services", "ETL Job"];
const ALERT_CONDITIONS = ["GT", "GTE", "LT", "LTE", "EQ", "NE", "MATCHES", "NOT_MATCHES", "MISSING"];
const LOG_SOURCES = ["FILE", "WINDOWS_EVENT", "JOURNALD", "API"];
const LOG_MODES = ["TAIL", "READ_ONCE", "EVENT_STREAM"];
const LOG_PARSERS = ["TEXT", "SYSLOG", "WINDOWS_EVENT", "PENTAHO", "JSON", "REGEX"];
const CHANNELS = ["EMAIL", "PAGERDUTY", "SERVICENOW"];

function clone(v) { return JSON.parse(JSON.stringify(v)); }
function meta(source) {
  try {
    const raw = typeof source?.connection_config === "string" ? JSON.parse(source.connection_config || "{}") : source?.connection_config || {};
    return raw.opscontrol || {};
  } catch { return {}; }
}
function normalizeTemplate(raw) {
  const p = clone(raw?.package_config || raw || {});
  return {
    id: raw?.id || p.id || "",
    name: raw?.name || p.name || "New Monitoring Template",
    description: raw?.description || p.description || "",
    scope: raw?.scope || p.scope || "VM + Application / Services",
    version: Number(raw?.version || p.version || 1),
    status: raw?.status || p.status || "DRAFT",
    committed_at: raw?.committed_at || null,
    attributes: Array.isArray(p.attributes) ? p.attributes : [],
    collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: [], ...(p.collector || {}) },
    metrics: Array.isArray(p.metrics) ? p.metrics : [],
    alerts: Array.isArray(p.alerts) ? p.alerts : [],
    logs: Array.isArray(p.logs) ? p.logs : [],
  };
}
function Field({ label, children, help }) {
  return <label className="form-field"><span>{label}</span>{children}{help && <small>{help}</small>}</label>;
}
function Modal({ title, children, onClose, wide = false }) {
  return <div className="modal-backdrop" onMouseDown={e => e.target === e.currentTarget && onClose()}>
    <div className={wide ? "modal resource-onboarding-modal" : "modal"}>
      <div className="modal-header"><div><div className="eyebrow">RESOURCE MANAGEMENT</div><h2>{title}</h2></div><button className="close-button" onClick={onClose}>×</button></div>
      {children}
    </div>
  </div>;
}

function OrgModal({ item, onClose, onSaved }) {
  const [form, setForm] = useState({ name: item?.name || "", code: item?.code || "", active: item?.active ?? true });
  const [error, setError] = useState("");
  const save = async e => {
    e.preventDefault();
    try {
      const value = item?.id ? await updateOrganization(item.id, form) : await createOrganization(form);
      onSaved(value);
    } catch (e2) { setError(e2.message || "Unable to save organization"); }
  };
  return <Modal title={item?.id ? "Edit Organization" : "Create Organization"} onClose={onClose}>
    {error && <div className="scope-banner error-banner">{error}</div>}
    <form className="resource-form" onSubmit={save}>
      <div className="form-grid"><Field label="Organization Name"><input required value={form.name} onChange={e => setForm(v => ({ ...v, name: e.target.value }))} /></Field><Field label="Short Code"><input required value={form.code} onChange={e => setForm(v => ({ ...v, code: e.target.value.toUpperCase() }))} /></Field></div>
      <label className="toggle"><input type="checkbox" checked={form.active} onChange={e => setForm(v => ({ ...v, active: e.target.checked }))} /><span>Active organization</span></label>
      <div className="form-footer"><span className="muted small">Organization is the customer ownership boundary.</span><div><button type="button" className="filter-button" onClick={onClose}>Cancel</button><button className="primary-button">Save</button></div></div>
    </form>
  </Modal>;
}

function TemplateEditor({ value, onClose, onSaved }) {
  const initial = normalizeTemplate(value || {});
  const [draft, setDraft] = useState(initial);
  const [saved, setSaved] = useState(clone(initial));
  const [tab, setTab] = useState("general");
  const [errors, setErrors] = useState([]);
  const [history, setHistory] = useState([]);
  const [newAttr, setNewAttr] = useState({ name: "", key: "", type: "TEXT", value_source: "DATA_SOURCE", required: false, defaultValue: "", description: "", example: "", allowedValues: [] });
  const [newMetric, setNewMetric] = useState({ name: "", metric: "", resource: "VM", method: "HOST_METRIC", unit: "", interval: 30, aggregation: "avg", window: 60, dimensions: [], enabled: true });
  const [newAlert, setNewAlert] = useState({ name: "", domain: "VM", signal: "", condition: "GT", threshold: 80, threshold_type: "NUMBER", duration: 300, recovery: "", severity: "WARNING", channels: ["EMAIL"], deduplication: "organization+data_source+rule", enabled: true });
  const [newLog, setNewLog] = useState({ name: "", source: "FILE", path: "", mode: "TAIL", parser: "TEXT", timestamp_format: "", multiline: false, include_patterns: [], exclude_patterns: [], interval: 30, retention: 30, enabled: true });
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const update = patch => setDraft(d => ({ ...d, ...patch }));
  const row = (section, i, patch) => setDraft(d => ({ ...d, [section]: d[section].map((x, n) => n === i ? { ...x, ...patch } : x) }));
  const remove = (section, i) => setDraft(d => ({ ...d, [section]: d[section].filter((_, n) => n !== i) }));

  const validate = () => {
    const e = [];
    if (!draft.name.trim()) e.push("Template name is required.");
    if (!draft.scope.trim()) e.push("Template scope is required.");
    if (!Number(draft.collector.interval) || draft.collector.interval < 5) e.push("Collector interval must be at least 5 seconds.");
    if (!Number(draft.collector.port) || draft.collector.port < 1 || draft.collector.port > 65535) e.push("Collector port must be between 1 and 65535.");
    const keys = new Set();
    draft.attributes.forEach((a, i) => { if (!a.name?.trim()) e.push("Attribute " + (i + 1) + " needs a name."); if (!a.key?.trim()) e.push("Attribute " + (i + 1) + " needs a key."); if (a.key && keys.has(a.key)) e.push("Duplicate attribute key: " + a.key); keys.add(a.key); if (["SELECT", "MULTI_SELECT"].includes(a.type) && !(a.allowedValues || []).length) e.push("Attribute " + (a.name || i + 1) + " needs allowed values."); });
    const metricKeys = new Set();
    draft.metrics.forEach((m, i) => { if (!m.name?.trim() || !m.metric?.trim()) e.push("Metric " + (i + 1) + " needs name and key."); if (m.metric && metricKeys.has(m.metric)) e.push("Duplicate metric key: " + m.metric); metricKeys.add(m.metric); if (!Number(m.interval) || m.interval < 5) e.push("Metric " + (m.name || i + 1) + " needs interval >= 5 seconds."); });
    draft.alerts.forEach((a, i) => { if (!a.name?.trim() || !a.signal?.trim()) e.push("Alert " + (i + 1) + " needs name and signal."); if (!Number(a.duration) || a.duration < 1) e.push("Alert " + (a.name || i + 1) + " needs a breach duration."); });
    draft.logs.forEach((l, i) => { if (!l.name?.trim() || !l.path?.trim()) e.push("Log rule " + (i + 1) + " needs name and path/source."); if (!Number(l.interval) || l.interval < 5) e.push("Log rule " + (l.name || i + 1) + " needs interval >= 5 seconds."); if (!Number(l.retention) || l.retention < 1) e.push("Log rule " + (l.name || i + 1) + " needs retention >= 1 day."); });
    setErrors(e); return e;
  };
  const commit = async () => {
    if (validate().length) return;
    const p = clone(draft); delete p.id; delete p.version; delete p.status; delete p.committed_at;
    const result = draft.id ? await updateMonitoringTemplate(draft.id, { name: draft.name, description: draft.description, scope: draft.scope, package_config: p, committed_by: "Admin" }) : await createMonitoringTemplate({ name: draft.name, description: draft.description, scope: draft.scope, package_config: p, committed_by: "Admin" });
    const next = normalizeTemplate(result); setDraft(clone(next)); setSaved(clone(next)); setErrors([]); onSaved(next);
  };
  const loadHistory = async () => { if (draft.id) setHistory(await fetchMonitoringTemplateVersions(draft.id)); };
  const add = (section, value, reset) => { setDraft(d => ({ ...d, [section]: [...d[section], clone(value)] })); reset(); };

  const renderAttributes = <div className="template-editor-panel">
    <div className="info-box">Attributes define the template contract. The Data Source supplies customer-specific values. Use PATH/DIRECTORY plus expressions such as \${PENTAHO_HOME} for reusable log paths.</div>
    {draft.attributes.map((a, i) => <div className="template-rule-card" key={i}>
      <div className="form-grid"><Field label="Display Name"><input value={a.name || ""} onChange={e => row("attributes", i, { name: e.target.value })} /></Field><Field label="Key"><input value={a.key || ""} onChange={e => row("attributes", i, { key: e.target.value })} /></Field></div>
      <div className="form-grid"><Field label="Type"><select value={a.type || "TEXT"} onChange={e => row("attributes", i, { type: e.target.value })}>{ATTR_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Value Source"><select value={a.value_source || "DATA_SOURCE"} onChange={e => row("attributes", i, { value_source: e.target.value })}>{VALUE_SOURCES.map(x => <option key={x}>{x}</option>)}</select></Field></div>
      <div className="form-grid"><Field label="Default / Expression"><input value={a.defaultValue || ""} onChange={e => row("attributes", i, { defaultValue: e.target.value })} /></Field><Field label="Example"><input value={a.example || ""} onChange={e => row("attributes", i, { example: e.target.value })} /></Field></div>
      <Field label="Description"><textarea value={a.description || ""} onChange={e => row("attributes", i, { description: e.target.value })} /></Field>
      <div className="form-grid"><Field label="Allowed Values"><input value={(a.allowedValues || []).join(", ")} onChange={e => row("attributes", i, { allowedValues: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} /></Field><label className="toggle"><input type="checkbox" checked={!!a.required} onChange={e => row("attributes", i, { required: e.target.checked })} /><span>Required</span></label></div>
      <button className="danger-button" type="button" onClick={() => remove("attributes", i)}>Remove Attribute</button>
    </div>)}
    <div className="builder-section"><div className="builder-section-title">Add Attribute</div><div className="form-grid"><Field label="Display Name"><input value={newAttr.name} onChange={e => setNewAttr(v => ({ ...v, name: e.target.value }))} /></Field><Field label="Key"><input value={newAttr.key} onChange={e => setNewAttr(v => ({ ...v, key: e.target.value }))} /></Field></div><div className="form-grid"><Field label="Type"><select value={newAttr.type} onChange={e => setNewAttr(v => ({ ...v, type: e.target.value }))}>{ATTR_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Value Source"><select value={newAttr.value_source} onChange={e => setNewAttr(v => ({ ...v, value_source: e.target.value }))}>{VALUE_SOURCES.map(x => <option key={x}>{x}</option>)}</select></Field></div><Field label="Description"><input value={newAttr.description} onChange={e => setNewAttr(v => ({ ...v, description: e.target.value }))} /></Field><button className="primary-button" type="button" onClick={() => add("attributes", newAttr, () => setNewAttr({ name: "", key: "", type: "TEXT", value_source: "DATA_SOURCE", required: false, defaultValue: "", description: "", example: "", allowedValues: [] }))}>+ Add Attribute</button></div>
  </div>;

  const renderMetrics = <div className="template-editor-panel"><div className="info-box">A metric rule defines what is measured, collection method, aggregation, window and dimensions.</div>{draft.metrics.map((m, i) => <div className="template-rule-card" key={i}>
    <div className="form-grid"><Field label="Metric Name"><input value={m.name || ""} onChange={e => row("metrics", i, { name: e.target.value })} /></Field><Field label="Metric Key"><input value={m.metric || ""} onChange={e => row("metrics", i, { metric: e.target.value })} /></Field></div>
    <div className="form-grid"><Field label="Resource"><select value={m.resource || "VM"} onChange={e => row("metrics", i, { resource: e.target.value })}><option>VM</option><option>Application</option><option>Service</option><option>ETL</option><option>Database</option></select></Field><Field label="Method"><select value={m.method || "HOST_METRIC"} onChange={e => row("metrics", i, { method: e.target.value })}>{METRIC_METHODS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
    <div className="form-grid"><Field label="Unit"><input value={m.unit || ""} onChange={e => row("metrics", i, { unit: e.target.value })} /></Field><Field label="Interval (sec)"><input type="number" min="5" value={m.interval || 30} onChange={e => row("metrics", i, { interval: Number(e.target.value) })} /></Field></div>
    <div className="form-grid"><Field label="Aggregation"><select value={m.aggregation || "avg"} onChange={e => row("metrics", i, { aggregation: e.target.value })}>{AGGREGATIONS.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Window (sec)"><input type="number" min="1" value={m.window || 60} onChange={e => row("metrics", i, { window: Number(e.target.value) })} /></Field></div>
    <Field label="Dimensions"><input value={(m.dimensions || []).join(", ")} onChange={e => row("metrics", i, { dimensions: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} placeholder="host, mount, process, service" /></Field>
    <button className="danger-button" type="button" onClick={() => remove("metrics", i)}>Remove Metric</button>
  </div>)}<div className="builder-section"><div className="builder-section-title">Add Metric Rule</div><div className="form-grid"><Field label="Metric Name"><input value={newMetric.name} onChange={e => setNewMetric(v => ({ ...v, name: e.target.value }))} /></Field><Field label="Metric Key"><input value={newMetric.metric} onChange={e => setNewMetric(v => ({ ...v, metric: e.target.value }))} placeholder="cpu.utilization" /></Field></div><div className="form-grid"><Field label="Resource"><select value={newMetric.resource} onChange={e => setNewMetric(v => ({ ...v, resource: e.target.value }))}><option>VM</option><option>Application</option><option>Service</option><option>ETL</option><option>Database</option></select></Field><Field label="Method"><select value={newMetric.method} onChange={e => setNewMetric(v => ({ ...v, method: e.target.value }))}>{METRIC_METHODS.map(x => <option key={x}>{x}</option>)}</select></Field></div><button className="primary-button" type="button" onClick={() => add("metrics", newMetric, () => setNewMetric({ name: "", metric: "", resource: "VM", method: "HOST_METRIC", unit: "", interval: 30, aggregation: "avg", window: 60, dimensions: [], enabled: true }))}>+ Add Metric</button></div></div>;

  const renderAlerts = <div className="template-editor-panel"><div className="info-box">Alerts can evaluate numeric thresholds, durations/SLA, missing signals and string patterns. Notifications and deduplication are part of the rule.</div>{draft.alerts.map((a, i) => <div className="template-rule-card" key={i}>
    <div className="form-grid"><Field label="Rule Name"><input value={a.name || ""} onChange={e => row("alerts", i, { name: e.target.value })} /></Field><Field label="Domain"><select value={a.domain || "VM"} onChange={e => row("alerts", i, { domain: e.target.value })}>{ALERT_DOMAINS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
    <div className="form-grid"><Field label="Signal / Metric / Event"><input value={a.signal || ""} onChange={e => row("alerts", i, { signal: e.target.value })} /></Field><Field label="Condition"><select value={a.condition || "GT"} onChange={e => row("alerts", i, { condition: e.target.value })}>{ALERT_CONDITIONS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
    <div className="form-grid"><Field label="Threshold / Pattern"><input value={a.threshold ?? ""} onChange={e => row("alerts", i, { threshold: e.target.value })} /></Field><Field label="Type"><select value={a.threshold_type || "NUMBER"} onChange={e => row("alerts", i, { threshold_type: e.target.value })}><option>NUMBER</option><option>STRING_PATTERN</option><option>DURATION</option></select></Field></div>
    <div className="form-grid"><Field label="Breach Duration (sec)"><input type="number" min="1" value={a.duration || 60} onChange={e => row("alerts", i, { duration: Number(e.target.value) })} /></Field><Field label="Recovery"><input value={a.recovery || ""} onChange={e => row("alerts", i, { recovery: e.target.value })} placeholder="LT 80 for 300s" /></Field></div>
    <div className="form-grid"><Field label="Severity"><select value={a.severity || "WARNING"} onChange={e => row("alerts", i, { severity: e.target.value })}><option>INFO</option><option>WARNING</option><option>CRITICAL</option></select></Field><Field label="Deduplication"><input value={a.deduplication || ""} onChange={e => row("alerts", i, { deduplication: e.target.value })} /></Field></div>
    <Field label="Notification Channels"><div className="check-grid">{CHANNELS.map(x => <label className="check-option" key={x}><input type="checkbox" checked={(a.channels || []).includes(x)} onChange={() => row("alerts", i, { channels: (a.channels || []).includes(x) ? a.channels.filter(v => v !== x) : [...(a.channels || []), x] })} /><span>{x}</span></label>)}</div></Field>
    <button className="danger-button" type="button" onClick={() => remove("alerts", i)}>Remove Alert</button>
  </div>)}<div className="builder-section"><div className="builder-section-title">Add Alert Rule</div><div className="form-grid"><Field label="Rule Name"><input value={newAlert.name} onChange={e => setNewAlert(v => ({ ...v, name: e.target.value }))} /></Field><Field label="Domain"><select value={newAlert.domain} onChange={e => setNewAlert(v => ({ ...v, domain: e.target.value }))}>{ALERT_DOMAINS.map(x => <option key={x}>{x}</option>)}</select></Field></div><div className="form-grid"><Field label="Signal"><input value={newAlert.signal} onChange={e => setNewAlert(v => ({ ...v, signal: e.target.value }))} /></Field><Field label="Condition"><select value={newAlert.condition} onChange={e => setNewAlert(v => ({ ...v, condition: e.target.value }))}>{ALERT_CONDITIONS.map(x => <option key={x}>{x}</option>)}</select></Field></div><div className="form-grid"><Field label="Threshold / Pattern"><input value={newAlert.threshold} onChange={e => setNewAlert(v => ({ ...v, threshold: e.target.value }))} /></Field><Field label="Breach Duration (sec)"><input type="number" min="1" value={newAlert.duration} onChange={e => setNewAlert(v => ({ ...v, duration: Number(e.target.value) }))} /></Field></div><button className="primary-button" type="button" onClick={() => add("alerts", newAlert, () => setNewAlert({ name: "", domain: "VM", signal: "", condition: "GT", threshold: 80, threshold_type: "NUMBER", duration: 300, recovery: "", severity: "WARNING", channels: ["EMAIL"], deduplication: "organization+data_source+rule", enabled: true }))}>+ Add Alert Rule</button></div></div>;

  const renderLogs = <div className="template-editor-panel"><div className="info-box">Log collection rules define the actual file/event source. This answers how OpsControl finds logs for a defined process: path + mode + parser + patterns.</div>{draft.logs.map((l, i) => <div className="template-rule-card" key={i}>
    <div className="form-grid"><Field label="Rule Name"><input value={l.name || ""} onChange={e => row("logs", i, { name: e.target.value })} /></Field><Field label="Source"><select value={l.source || "FILE"} onChange={e => row("logs", i, { source: e.target.value })}>{LOG_SOURCES.map(x => <option key={x}>{x}</option>)}</select></Field></div>
    <Field label="Path / Source"><input value={l.path || ""} onChange={e => row("logs", i, { path: e.target.value })} placeholder="C:\\Pentaho\\logs\\*.log or /var/log/*.log" /></Field>
    <div className="form-grid"><Field label="Mode"><select value={l.mode || "TAIL"} onChange={e => row("logs", i, { mode: e.target.value })}>{LOG_MODES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Parser"><select value={l.parser || "TEXT"} onChange={e => row("logs", i, { parser: e.target.value })}>{LOG_PARSERS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
    <div className="form-grid"><Field label="Timestamp Format"><input value={l.timestamp_format || ""} onChange={e => row("logs", i, { timestamp_format: e.target.value })} /></Field><Field label="Interval (sec)"><input type="number" min="5" value={l.interval || 30} onChange={e => row("logs", i, { interval: Number(e.target.value) })} /></Field></div>
    <div className="form-grid"><Field label="Include Patterns"><input value={(l.include_patterns || []).join(", ")} onChange={e => row("logs", i, { include_patterns: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} /></Field><Field label="Exclude Patterns"><input value={(l.exclude_patterns || []).join(", ")} onChange={e => row("logs", i, { exclude_patterns: e.target.value.split(",").map(x => x.trim()).filter(Boolean) })} /></Field></div>
    <div className="form-grid"><Field label="Retention (days)"><input type="number" min="1" value={l.retention || 30} onChange={e => row("logs", i, { retention: Number(e.target.value) })} /></Field><label className="toggle"><input type="checkbox" checked={!!l.multiline} onChange={e => row("logs", i, { multiline: e.target.checked })} /><span>Multiline events</span></label></div>
    <button className="danger-button" type="button" onClick={() => remove("logs", i)}>Remove Log Rule</button>
  </div>)}<div className="builder-section"><div className="builder-section-title">Add Log Collection Rule</div><div className="form-grid"><Field label="Rule Name"><input value={newLog.name} onChange={e => setNewLog(v => ({ ...v, name: e.target.value }))} /></Field><Field label="Source"><select value={newLog.source} onChange={e => setNewLog(v => ({ ...v, source: e.target.value }))}>{LOG_SOURCES.map(x => <option key={x}>{x}</option>)}</select></Field></div><Field label="Path / Source"><input value={newLog.path} onChange={e => setNewLog(v => ({ ...v, path: e.target.value }))} /></Field><div className="form-grid"><Field label="Mode"><select value={newLog.mode} onChange={e => setNewLog(v => ({ ...v, mode: e.target.value }))}>{LOG_MODES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Parser"><select value={newLog.parser} onChange={e => setNewLog(v => ({ ...v, parser: e.target.value }))}>{LOG_PARSERS.map(x => <option key={x}>{x}</option>)}</select></Field></div><button className="primary-button" type="button" onClick={() => add("logs", newLog, () => setNewLog({ name: "", source: "FILE", path: "", mode: "TAIL", parser: "TEXT", timestamp_format: "", multiline: false, include_patterns: [], exclude_patterns: [], interval: 30, retention: 30, enabled: true }))}>+ Add Log Rule</button></div></div>;

  const tabs = [["general", "General"], ["attributes", "Attributes"], ["collector", "Collector / Agent"], ["metrics", "Metrics"], ["alerts", "Alert Rules"], ["logs", "Log Collection"]];
  return <Modal title={draft.id ? "Edit Monitoring Template" : "Create Monitoring Template"} wide onClose={onClose}>
    <div className="template-editor-header"><div><div className="template-editor-name-row"><h3>{draft.name}</h3><span className={dirty ? "template-draft-badge dirty" : "template-draft-badge"}>{dirty ? "UNSAVED CHANGES" : draft.status}</span><span className="template-version-badge">v{draft.version}</span></div><small className="muted">Design → Validate → Apply &amp; Commit</small></div><button className="filter-button" type="button" onClick={loadHistory}>Version History</button></div>
    {history.length > 0 && <div className="template-history-panel"><b>Version History</b>{history.map(v => <div className="template-history-row" key={v.id}><span>v{v.version}</span><b>{v.status}</b><span>{new Date(v.committed_at).toLocaleString("en-IN")}</span><span>{v.committed_by || "Admin"}</span></div>)}</div>}
    <div className="template-editor-layout"><aside className="template-editor-side-tabs">{tabs.map(([k, label]) => <button type="button" key={k} className={tab === k ? "template-side-tab active" : "template-side-tab"} onClick={() => setTab(k)}>{label}<span>{k === "attributes" ? draft.attributes.length : k === "metrics" ? draft.metrics.length : k === "alerts" ? draft.alerts.length : k === "logs" ? draft.logs.length : ""}</span></button>)}</aside><section className="template-editor-content">
      {tab === "general" && <div className="template-editor-panel"><div className="form-grid"><Field label="Template Name"><input value={draft.name} onChange={e => update({ name: e.target.value })} /></Field><Field label="Scope"><input value={draft.scope} onChange={e => update({ scope: e.target.value })} /></Field></div><Field label="Description"><textarea value={draft.description} onChange={e => update({ description: e.target.value })} /></Field><div className="template-general-summary">{[["Attributes", draft.attributes.length], ["Metrics", draft.metrics.length], ["Alerts", draft.alerts.length], ["Logs", draft.logs.length], ["Collector signals", draft.collector.telemetry.length]].map(x => <div key={x[0]}><span>{x[0]}</span><b>{x[1]}</b></div>)}</div></div>}
      {tab === "attributes" && renderAttributes}
      {tab === "collector" && <div className="template-editor-panel"><div className="info-box">Collector defaults belong to the template; installation/registration belongs to Data Source onboarding.</div><div className="form-grid"><Field label="Type"><select value={draft.collector.type} onChange={e => update({ collector: { ...draft.collector, type: e.target.value } })}><option>OTEL</option><option>WINDOWS</option><option>LINUX</option><option>PENTAHO</option></select></Field><Field label="Interval (sec)"><input type="number" min="5" value={draft.collector.interval} onChange={e => update({ collector: { ...draft.collector, interval: Number(e.target.value) } })} /></Field></div><div className="form-grid"><Field label="Protocol"><select value={draft.collector.protocol} onChange={e => update({ collector: { ...draft.collector, protocol: e.target.value } })}><option>OTLP/gRPC</option><option>OTLP/HTTP</option></select></Field><Field label="Port"><input type="number" min="1" max="65535" value={draft.collector.port} onChange={e => update({ collector: { ...draft.collector, port: Number(e.target.value) } })} /></Field></div><label className="toggle"><input type="checkbox" checked={!!draft.collector.tls} onChange={e => update({ collector: { ...draft.collector, tls: e.target.checked } })} /><span>TLS enabled</span></label><Field label="Telemetry capabilities"><div className="check-grid">{TELEMETRY.map(x => <label className="check-option" key={x}><input type="checkbox" checked={(draft.collector.telemetry || []).includes(x)} onChange={() => update({ collector: { ...draft.collector, telemetry: (draft.collector.telemetry || []).includes(x) ? draft.collector.telemetry.filter(v => v !== x) : [...(draft.collector.telemetry || []), x] } })} /><span>{x}</span></label>)}</div></Field></div>}
      {tab === "metrics" && renderMetrics}
      {tab === "alerts" && renderAlerts}
      {tab === "logs" && renderLogs}
    </section></div>
    {errors.length > 0 && <div className="template-validation-panel"><b>Validation failed</b>{errors.map((x, i) => <div key={i}>• {x}</div>)}</div>}
    <div className="form-footer template-commit-footer"><div><span className={dirty ? "template-change-indicator dirty" : "template-change-indicator"}>{dirty ? "● Unsaved changes" : "✓ No unsaved changes"}</span></div><div><button type="button" className="filter-button" onClick={validate}>Validate</button><button type="button" className="filter-button" disabled={!dirty} onClick={() => { setDraft(clone(saved)); setErrors([]); }}>Discard</button><button type="button" className="primary-button" disabled={!dirty} onClick={commit}>Apply &amp; Commit Changes</button></div></div>
  </Modal>;
}

function DataSourceWizard({ organizations, templates, initial, onClose, onSaved }) {
  const [step, setStep] = useState(1);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(initial || { organization_id: organizations.find(o => o.active)?.id || "", name: "", visible_name: "", hostname: "", environment: "PROD", os_type: "Windows", workload_roles: ["Application"], product_family: "SLM", product: "SPM", host_groups: ["PROD"], templates: [], description: "" });
  const [agent, setAgent] = useState({ name: "", mode: "DNS", ip: "", port: 4317, protocol: "OTLP/gRPC", tls: true, vault: "", install_method: "PACKAGE", version: "latest", telemetry: ["VM metrics", "System logs", "Application logs", "Services"] });
  const [orgEditor, setOrgEditor] = useState(null);
  const update = patch => setForm(v => ({ ...v, ...patch }));
  const toggle = (key, val) => update({ [key]: form[key].includes(val) ? form[key].filter(x => x !== val) : [...form[key], val] });
  const toggleAgent = val => setAgent(v => ({ ...v, telemetry: v.telemetry.includes(val) ? v.telemetry.filter(x => x !== val) : [...v.telemetry, val] }));

  const save = async () => {
    setSaving(true); setError("");
    try {
      const chosen = templates.filter(t => form.templates.includes(t.id));
      const config = { opscontrol: { ...meta(initial), visible_name: form.visible_name || form.name, hostname: form.hostname, environment: form.environment, workload_roles: form.workload_roles, server_type: form.workload_roles.length > 1 ? "Multi-role" : form.workload_roles[0], os_type: form.os_type, product_family: form.product_family, product: form.product, host_groups: form.host_groups, template_ids: form.templates, templates: chosen.map(t => t.name) } };
      const source = initial?.id ? await updateDataSource(initial.id, { name: form.name || form.hostname, endpoint: form.hostname, description: form.description || null, connection_config: { ...(initial.connection_config || {}), ...config } }) : await createDataSource({ organization_id: form.organization_id, name: form.name || form.hostname, source_type: form.os_type.toUpperCase(), endpoint: form.hostname, description: form.description || null, auth_type: "PTC_VAULT", connection_config: config, enabled: true });
      const existing = await fetchDataSourceTemplates(source.id).catch(() => []);
      const wanted = new Set(form.templates);
      for (const a of existing) if (!wanted.has(a.template_id)) await detachDataSourceTemplate(source.id, a.template_id);
      for (const t of chosen) {
        const current = existing.find(a => a.template_id === t.id);
        if (current) await updateDataSourceTemplate(source.id, t.id, { template_version: Number(t.version || current.template_version), priority: current.priority, overrides: current.overrides || null, enabled: true });
        else await attachDataSourceTemplate(source.id, { template_id: t.id, template_version: Number(t.version || 1), priority: 100, overrides: null });
      }
      if (!initial?.id) await createCollector({ data_source_id: source.id, name: agent.name || form.hostname + "-Agent", collector_type: "OTEL", enabled: true, interval_seconds: 30, configuration: { provider: "opentelemetry", agent: { install_status: "PENDING_INSTALL", install_method: agent.install_method, version: agent.version }, connection: { mode: agent.mode, ip_address: agent.ip, dns_name: form.hostname, port: Number(agent.port), protocol: agent.protocol, tls: agent.tls }, credential_provider: "PTC_VAULT", vault_secret_ref: agent.vault || null, telemetry: agent.telemetry, template_ids: form.templates } });
      await fetchEffectiveDataSourceConfiguration(source.id);
      onSaved();
    } catch (e) { setError(e.message || "Unable to save Data Source"); }
    finally { setSaving(false); }
  };

  return <Modal title={initial?.id ? "Edit Data Source" : "Add Data Source"} wide onClose={() => !saving && onClose()}>
    <div className="onboarding-steps">{["Organization", "Data Source", "Templates", "Agent & Collector", "Review"].map((x, i) => <div key={x} className={step === i + 1 ? "onboarding-step active" : step > i + 1 ? "onboarding-step complete" : "onboarding-step"}><span>{step > i + 1 ? "✓" : i + 1}</span>{x}</div>)}</div>
    {step === 1 && <div className="resource-form"><div className="info-box">Start with the customer boundary. Organization can be created or edited without leaving onboarding.</div><Field label="Organization"><select value={form.organization_id} onChange={e => update({ organization_id: e.target.value })}>{organizations.filter(o => o.active || o.id === form.organization_id).map(o => <option key={o.id} value={o.id}>{o.name} ({o.code})</option>)}</select></Field><div className="heading-actions"><button type="button" className="filter-button" onClick={() => setOrgEditor({})}>+ Create Organization</button>{form.organization_id && <button type="button" className="filter-button" onClick={() => setOrgEditor(organizations.find(o => o.id === form.organization_id))}>Edit Selected Organization</button>}</div><div className="form-footer"><span className="muted small">Step 1 of 5</span><button type="button" className="primary-button" disabled={!form.organization_id} onClick={() => setStep(2)}>Next: Data Source →</button></div>{orgEditor && <OrgModal item={orgEditor.id ? orgEditor : null} onClose={() => setOrgEditor(null)} onSaved={() => { setOrgEditor(null); onSaved(); }} />}</div>}
    {step === 2 && <div className="resource-form"><div className="info-box">A Data Source is a customer VM/machine. Workload Roles are multi-select, so a VM can be both ETL and Application.</div><div className="form-grid"><Field label="Host Name"><input required value={form.hostname} onChange={e => update({ hostname: e.target.value, name: form.name || e.target.value })} /></Field><Field label="Visible Name"><input value={form.visible_name} onChange={e => update({ visible_name: e.target.value })} /></Field></div><div className="form-grid"><Field label="Environment"><select value={form.environment} onChange={e => update({ environment: e.target.value })}>{ENVIRONMENTS.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="OS Type"><select value={form.os_type} onChange={e => update({ os_type: e.target.value })}>{OS_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field></div><Field label="Workload Roles"><div className="check-grid">{ROLES.map(x => <label className="check-option" key={x}><input type="checkbox" checked={form.workload_roles.includes(x)} onChange={() => toggle("workload_roles", x)} /><span>{x}</span></label>)}</div></Field><div className="form-grid"><Field label="Product Family"><input value={form.product_family} onChange={e => update({ product_family: e.target.value })} /></Field><Field label="Product"><select value={form.product} onChange={e => update({ product: e.target.value })}>{PRODUCTS.map(x => <option key={x}>{x}</option>)}</select></Field></div><Field label="Host Groups"><div className="check-grid">{HOST_GROUPS.map(x => <label className="check-option" key={x}><input type="checkbox" checked={form.host_groups.includes(x)} onChange={() => toggle("host_groups", x)} /><span>{x}</span></label>)}</div></Field><Field label="Description"><textarea value={form.description} onChange={e => update({ description: e.target.value })} /></Field><div className="form-footer"><button className="filter-button" type="button" onClick={() => setStep(1)}>← Organization</button><button className="primary-button" type="button" disabled={!form.hostname || !form.workload_roles.length} onClick={() => setStep(3)}>Next: Templates →</button></div></div>}
    {step === 3 && <div className="resource-form"><div className="info-box">Select one or more policy packages. The effective configuration is resolved from pinned template versions plus Data Source overrides.</div><div className="template-grid">{templates.filter(t => t.status !== "DISABLED").map(t => <button type="button" className={form.templates.includes(t.id) ? "template-card selected" : "template-card"} key={t.id} onClick={() => toggle("templates", t.id)}><div className="template-card-head"><div><b>{t.name}</b><small>{t.scope} · v{t.version}</small></div><span className="template-check">{form.templates.includes(t.id) ? "✓" : "+"}</span></div><p>{t.description}</p><div className="template-example-list"><span>{t.metrics.length} metrics</span><span>{t.alerts.length} alerts</span><span>{t.logs.length} log rules</span></div></button>)}</div><div className="form-footer"><button className="filter-button" type="button" onClick={() => setStep(2)}>← Data Source</button><button className="primary-button" type="button" onClick={() => setStep(4)}>Next: Agent & Collector →</button></div></div>}
    {step === 4 && <div className="resource-form"><div className="info-box"><b>Agent onboarding:</b> this records the install method, version, endpoint, Vault reference and telemetry capabilities. Actual installer/runtime remains Phase 3.</div><Field label="Agent / Collector Name"><input value={agent.name} onChange={e => setAgent(v => ({ ...v, name: e.target.value }))} placeholder="HOST-Agent" /></Field><div className="form-grid"><Field label="Connection Mode"><select value={agent.mode} onChange={e => setAgent(v => ({ ...v, mode: e.target.value }))}><option>DNS</option><option>IP</option></select></Field><Field label="Port"><input type="number" min="1" max="65535" value={agent.port} onChange={e => setAgent(v => ({ ...v, port: Number(e.target.value) }))} /></Field></div><div className="form-grid"><Field label="IP Address"><input value={agent.ip} onChange={e => setAgent(v => ({ ...v, ip: e.target.value }))} /></Field><Field label="Protocol"><select value={agent.protocol} onChange={e => setAgent(v => ({ ...v, protocol: e.target.value }))}><option>OTLP/gRPC</option><option>OTLP/HTTP</option></select></Field></div><div className="form-grid"><Field label="Install Method"><select value={agent.install_method} onChange={e => setAgent(v => ({ ...v, install_method: e.target.value }))}><option>PACKAGE</option><option>SCRIPT</option><option>MANUAL</option></select></Field><Field label="Agent Version"><input value={agent.version} onChange={e => setAgent(v => ({ ...v, version: e.target.value }))} /></Field></div><Field label="PTC Vault Secret Reference"><input value={agent.vault} onChange={e => setAgent(v => ({ ...v, vault: e.target.value }))} /></Field><Field label="Telemetry"><div className="check-grid">{TELEMETRY.map(x => <label className="check-option" key={x}><input type="checkbox" checked={agent.telemetry.includes(x)} onChange={() => toggleAgent(x)} /><span>{x}</span></label>)}</div></Field><label className="toggle"><input type="checkbox" checked={agent.tls} onChange={e => setAgent(v => ({ ...v, tls: e.target.checked }))} /><span>TLS enabled</span></label><div className="form-footer"><button className="filter-button" type="button" onClick={() => setStep(3)}>← Templates</button><button className="primary-button" type="button" onClick={() => setStep(5)}>Review →</button></div></div>}
    {step === 5 && <div className="resource-form">{error && <div className="scope-banner error-banner">{error}</div>}<div className="review-grid"><div className="card review-card"><span>Organization</span><b>{organizations.find(o => o.id === form.organization_id)?.name || "—"}</b><small>{form.environment}</small></div><div className="card review-card"><span>Data Source</span><b>{form.visible_name || form.name || form.hostname}</b><small>{form.hostname} · {form.os_type}</small></div><div className="card review-card"><span>Workload Roles</span><b>{form.workload_roles.join(", ")}</b><small>{form.product_family} · {form.product}</small></div><div className="card review-card"><span>Templates</span><b>{form.templates.length || "None"}</b><small>{templates.filter(t => form.templates.includes(t.id)).map(t => t.name).join(", ") || "No template selected"}</small></div><div className="card review-card"><span>Agent</span><b>{agent.name || form.hostname + "-Agent"}</b><small>{agent.install_method} · {agent.version} · PENDING INSTALL</small></div><div className="card review-card"><span>Telemetry</span><b>{agent.telemetry.length} capabilities</b><small>{agent.telemetry.join(", ")}</small></div></div><div className="form-footer"><button className="filter-button" type="button" onClick={() => setStep(4)}>← Agent & Collector</button><button className="primary-button" type="button" disabled={saving} onClick={save}>{saving ? "Saving..." : initial?.id ? "Save Data Source" : "Create Data Source + Agent Configuration"}</button></div></div>}
  </Modal>;
}

export default function ResourceManagementV2({ organizationIds = [] }) {
  const [tab, setTab] = useState("organizations");
  const [organizations, setOrganizations] = useState([]);
  const [dataSources, setDataSources] = useState([]);
  const [collectors, setCollectors] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [orgEditor, setOrgEditor] = useState(null);
  const [wizard, setWizard] = useState(null);
  const [templateEditor, setTemplateEditor] = useState(null);
  const reload = async () => {
    setLoading(true); setError("");
    try {
      const orgs = await fetchOrganizations();
      setOrganizations(orgs);
      const ids = organizationIds.length ? organizationIds : orgs.map(o => o.id);
      const sources = ids.length ? await fetchDataSources({ organization_id: ids }) : [];
      setDataSources(sources);
      const sourceIds = sources.map(s => s.id);
      setCollectors(sourceIds.length ? await fetchCollectors({ data_source_id: sourceIds }) : []);
      const remote = await fetchMonitoringTemplates();
      setTemplates(remote.map(normalizeTemplate));
    } catch (e) { setError(e.message || "Unable to load Resource Management"); }
    finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, [JSON.stringify(organizationIds)]);
  const orgMap = useMemo(() => new Map(organizations.map(x => [x.id, x])), [organizations]);
  const filteredSources = useMemo(() => {
    const q = query.toLowerCase().trim();
    return dataSources.filter(s => !q || [s.name, s.endpoint, meta(s).visible_name, meta(s).hostname, meta(s).environment, meta(s).workload_roles, meta(s).product].flat().join(" ").toLowerCase().includes(q));
  }, [dataSources, query]);
  const filteredCollectors = useMemo(() => {
    const q = query.toLowerCase().trim();
    return collectors.filter(c => { const s = dataSources.find(x => x.id === c.data_source_id); return !q || [c.name, s?.name, meta(s).visible_name].join(" ").toLowerCase().includes(q); });
  }, [collectors, dataSources, query]);
  const editSource = async source => {
    const m = meta(source); const a = await fetchDataSourceTemplates(source.id).catch(() => []);
    setWizard({ initial: { ...source, organization_id: source.organization_id, name: source.name, visible_name: m.visible_name || source.name, hostname: m.hostname || source.endpoint || "", environment: m.environment || "PROD", os_type: m.os_type || "Windows", workload_roles: m.workload_roles || (m.server_type ? [m.server_type] : ["Application"]), product_family: m.product_family || "SLM", product: m.product || "SPM", host_groups: m.host_groups || [], templates: a.filter(x => x.enabled).map(x => x.template_id), description: source.description || "" } });
  };
  const disable = async (fn, item) => { if (!window.confirm("Disable " + (item.name || "this resource") + "?")) return; try { await fn(item.id); await reload(); } catch (e) { setError(e.message || "Unable to disable resource"); } };
  const summary = [["organizations", "Organizations", organizations.length, "Customer boundaries"], ["data-sources", "Data Sources", dataSources.length, "Customer machines"], ["collectors", "Collectors", collectors.length, "Installed agents"], ["templates", "Templates", templates.length, "Monitoring policy packages"]];
  return <div className="resource-page">
    <div className="page-heading"><div><h1>Resource Management</h1><p>Organization → Data Source → Templates → Agent & Collector.</p></div><div className="heading-actions"><button className="filter-button" onClick={reload}>Refresh</button><button className="primary-button" disabled={!organizations.some(o => o.active)} onClick={() => setWizard({ initial: null })}>+ Add Data Source</button></div></div>
    <div className="resource-summary-grid">{summary.map(x => <button type="button" key={x[0]} className="card resource-summary-card resource-summary-link" onClick={() => { setTab(x[0]); setQuery(""); }}><span>{x[1]}</span><b>{x[2]}</b><small>{x[3]}</small><em>Open list →</em></button>)}</div>
    <div className="resource-layout"><aside className="resource-sidebar card">{NAV.map(([key, title, subtitle]) => <button key={key} className={tab === key ? "resource-tab active" : "resource-tab"} onClick={() => { setTab(key); setQuery(""); }}><b>{title}</b><small>{subtitle}</small></button>)}</aside>
      <section className="resource-main">{error && <div className="scope-banner error-banner">{error}</div>}{loading ? <div className="card state-panel"><div className="spinner" /><h3>Loading Resource Management</h3></div> : <>
        {tab === "organizations" && <div className="resource-section-stack"><div className="card resource-toolbar"><div><h2>Organizations</h2><span className="muted small">Create, edit and deactivate customer boundaries.</span></div><button className="primary-button" onClick={() => setOrgEditor({})}>+ Create Organization</button></div><div className="organization-grid">{organizations.map(o => <div className="card organization-card" key={o.id}><div className="organization-card-head"><div><b>{o.name}</b><small>{o.code}</small></div><span className={o.active ? "status status--success" : "status status--unknown"}>{o.active ? "ACTIVE" : "INACTIVE"}</span></div><div className="organization-fields"><div><span>Data Sources</span><b>{dataSources.filter(s => s.organization_id === o.id).length}</b></div><div><span>Collectors</span><b>{collectors.filter(c => dataSources.some(s => s.organization_id === o.id && s.id === c.data_source_id)).length}</b></div><div><span>Isolation</span><b>Scoped</b></div></div><div className="row-actions"><button className="filter-button" onClick={() => setOrgEditor(o)}>Edit</button>{o.active && <button className="danger-button" onClick={() => disable(disableOrganization, o)}>Disable</button>}</div></div>)}</div></div>}
        {tab === "data-sources" && <div className="resource-section-stack"><div className="card resource-toolbar"><div><h2>Data Sources</h2><span className="muted small">One customer VM/machine can have multiple workload roles.</span></div><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search hostname, role, product..." /></div><div className="card table-wrap"><table><thead><tr><th>Data Source</th><th>Organization</th><th>Environment</th><th>Workload Roles</th><th>OS / Product</th><th>Templates</th><th>Agent</th><th>Actions</th></tr></thead><tbody>{filteredSources.map(s => { const m = meta(s); const cs = collectors.filter(c => c.data_source_id === s.id); return <tr key={s.id}><td><b>{m.visible_name || s.name}</b><small>{m.hostname || s.endpoint}</small></td><td>{orgMap.get(s.organization_id)?.name || "—"}</td><td>{m.environment || "—"}</td><td><div className="chip-row">{(m.workload_roles || [m.server_type]).map(x => <span className="mini-chip" key={x}>{x}</span>)}</div></td><td>{m.os_type || "—"}<small>{m.product_family || ""} / {m.product || ""}</small></td><td>{(m.templates || []).join(", ") || "—"}</td><td>{cs.length ? cs[0].status : "NO AGENT"}</td><td><div className="row-actions"><button className="filter-button" onClick={() => editSource(s)}>Edit</button>{s.enabled && <button className="danger-button" onClick={() => disable(disableDataSource, s)}>Disable</button>}</div></td></tr>})}</tbody></table></div></div>}
        {tab === "collectors" && <div className="resource-section-stack"><div className="card resource-toolbar"><div><h2>Collectors & Agents</h2><span className="muted small">Installation registration and telemetry capabilities.</span></div><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search collector or Data Source..." /></div><div className="card table-wrap"><table><thead><tr><th>Agent</th><th>Data Source</th><th>Organization</th><th>Install</th><th>Telemetry</th><th>Status</th><th>Actions</th></tr></thead><tbody>{filteredCollectors.map(c => { const s = dataSources.find(x => x.id === c.data_source_id); const cfg = c.configuration || {}; return <tr key={c.id}><td><b>{c.name}</b><small>{c.collector_type}</small></td><td>{meta(s).visible_name || s?.name || "—"}</td><td>{orgMap.get(s?.organization_id)?.name || "—"}</td><td>{cfg.agent?.install_status || "PENDING INSTALL"}<small>{cfg.agent?.version || "latest"}</small></td><td>{(cfg.telemetry || []).join(", ")}</td><td>{c.status || "STOPPED"}</td><td><div className="row-actions"><button className="filter-button" onClick={() => editSource(s)}>Configure</button>{c.enabled && <button className="danger-button" onClick={() => disable(disableCollector, c)}>Disable</button>}</div></td></tr>})}</tbody></table></div></div>}
        {tab === "templates" && <div className="resource-section-stack"><div className="card resource-toolbar"><div><h2>Monitoring Templates</h2><span className="muted small">Collector + attributes + metrics + alert rules + log collection.</span></div><button className="primary-button" onClick={() => setTemplateEditor({})}>+ Create Template</button></div><div className="template-admin-grid">{templates.map(t => <div className="card template-admin-card" key={t.id}><div className="template-admin-head"><div><b>{t.name}</b><small>{t.scope} · v{t.version}</small></div><span className={t.status === "DISABLED" ? "status status--unknown" : "status status--success"}>{t.status}</span></div><p>{t.description}</p><div className="template-counts"><span>{t.attributes.length} attributes</span><span>{t.metrics.length} metrics</span><span>{t.alerts.length} alerts</span><span>{t.logs.length} log rules</span></div><div className="row-actions"><button className="filter-button" onClick={() => setTemplateEditor(t)}>Edit</button>{t.status !== "DISABLED" && <button className="danger-button" onClick={() => disable(disableMonitoringTemplate, t)}>Disable</button>}</div></div>)}</div></div>}
      </>}</section>
    </div>
    {orgEditor && <OrgModal item={orgEditor.id ? orgEditor : null} onClose={() => setOrgEditor(null)} onSaved={async () => { setOrgEditor(null); await reload(); }} />}
    {wizard && <DataSourceWizard organizations={organizations} templates={templates} initial={wizard.initial} onClose={() => setWizard(null)} onSaved={async () => { setWizard(null); await reload(); }} />}
    {templateEditor && <TemplateEditor value={templateEditor} onClose={() => setTemplateEditor(null)} onSaved={async () => { setTemplateEditor(null); await reload(); }} />}
  </div>;
}
