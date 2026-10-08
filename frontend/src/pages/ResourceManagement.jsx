import { useEffect, useMemo, useState } from "react";
import {
  createCollector, createDataSource, fetchCollectors, fetchDataSources,
  fetchOrganizations, updateDataSource,
} from "../api";

const NAV = [
  ["organizations", "Organizations", "Customers and service ownership"],
  ["data-sources", "Data Sources", "Customer machines and environments"],
  ["collectors", "Collectors", "Installed OTEL agents"],
  ["templates", "Templates", "Reusable monitoring packages"],
];

const ENVIRONMENTS = ["PROD", "QA", "TEST", "DEV", "SANDBOX"];
const SERVER_TYPES = ["Application Server", "Database Server", "ETL Server", "Other"];
const OS_TYPES = ["Windows", "Linux"];
const PRODUCTS = ["SPM", "SPP"];
const HOST_GROUPS = ["PROD", "QA", "TEST", "DEV", "SANDBOX", "SLM", "SPM", "SPP", "Windows Servers", "Linux Servers", "Application Servers", "Database Servers", "ETL Servers"];
const TELEMETRY = ["VM metrics", "System logs", "Application logs", "ETL logs", "Services", "Traces"];

const DEFAULT_DEFAULT_TEMPLATES = [
  {
    id: "windows-application", name: "Windows Application Server",
    description: "Windows infrastructure, services, application logs and standard health checks.",
    scope: "VM + Application / Services",
    collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: ["VM metrics","System logs","Application logs","Services"] },
    metrics: [
      { name: "CPU Utilization", metric: "cpu.utilization", resource: "VM", unit: "%", interval: 30, enabled: true },
      { name: "Memory Utilization", metric: "memory.utilization", resource: "VM", unit: "%", interval: 30, enabled: true },
      { name: "Disk Utilization", metric: "disk.utilization", resource: "VM", unit: "%", interval: 60, enabled: true },
    ],
    alerts: [
      { name: "High CPU", domain: "VM", metric: "CPU Utilization", severity: "WARNING", operator: "GT", threshold: 85, window: 300, consecutive: 3, notifications: ["EMAIL"] },
      { name: "Critical CPU", domain: "VM", metric: "CPU Utilization", severity: "CRITICAL", operator: "GT", threshold: 95, window: 300, consecutive: 2, notifications: ["EMAIL","PAGERDUTY"] },
    ],
    logs: [
      { name: "Windows Event Logs", source: "WINDOWS_EVENT", location: "Windows Event Viewer", parser: "WINDOWS_EVENT", severity: "WARNING+", interval: 30, retention: 30, enabled: true },
    ],
  },
  {
    id: "linux-database", name: "Linux Database Server",
    description: "Linux host telemetry with database/application log collection defaults.",
    scope: "VM + Application / Services",
    collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: ["VM metrics","System logs","Application logs","Services"] },
    metrics: [
      { name: "CPU Utilization", metric: "cpu.utilization", resource: "VM", unit: "%", interval: 30, enabled: true },
      { name: "Memory Utilization", metric: "memory.utilization", resource: "VM", unit: "%", interval: 30, enabled: true },
      { name: "Disk Utilization", metric: "disk.utilization", resource: "VM", unit: "%", interval: 60, enabled: true },
    ],
    alerts: [
      { name: "High Disk", domain: "VM", metric: "Disk Utilization", severity: "WARNING", operator: "GT", threshold: 85, window: 300, consecutive: 3, notifications: ["EMAIL"] },
    ],
    logs: [
      { name: "Linux System Logs", source: "FILE", location: "/var/log/*.log", parser: "SYSLOG", severity: "WARNING+", interval: 30, retention: 30, enabled: true },
    ],
  },
  {
    id: "pentaho-server", name: "Pentaho Server",
    description: "ETL-oriented defaults for Pentaho/Kettle and batch job telemetry.",
    scope: "VM + ETL",
    collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: ["VM metrics","System logs","ETL logs","Services"] },
    metrics: [
      { name: "CPU Utilization", metric: "cpu.utilization", resource: "VM", unit: "%", interval: 30, enabled: true },
      { name: "Disk Utilization", metric: "disk.utilization", resource: "VM", unit: "%", interval: 60, enabled: true },
    ],
    alerts: [
      { name: "ETL Long Running", domain: "ETL", metric: "Job Runtime", severity: "WARNING", operator: "GT", threshold: 1800, window: 300, consecutive: 1, notifications: ["EMAIL"] },
    ],
    logs: [
      { name: "Pentaho Logs", source: "FILE", location: "/opt/pentaho/logs/*.log", parser: "PENTAHO", severity: "ERROR+", interval: 15, retention: 30, enabled: true },
    ],
  },
  {
    id: "web-ui", name: "SLM Web UI", description: "WebUI/Tomcat/Apache monitoring defaults for SLM application servers.",
    scope: "Application / Services",
    collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: ["Application logs","Services","Traces"] },
    metrics: [{ name: "HTTP Response Time", metric: "http.server.duration", resource: "Application", unit: "ms", interval: 30, enabled: true }],
    alerts: [{ name: "HTTP Response Slow", domain: "Application / Services", metric: "HTTP Response Time", severity: "WARNING", operator: "GT", threshold: 2000, window: 300, consecutive: 3, notifications: ["EMAIL"] }],
    logs: [{ name: "Apache / Tomcat Logs", source: "FILE", location: "/opt/*/logs/*.log", parser: "TEXT", severity: "ERROR+", interval: 30, retention: 30, enabled: true }],
  },
  {
    id: "ssl", name: "SSL / Certificate", description: "Certificate and TLS monitoring defaults for customer endpoints.",
    scope: "Application / Services",
    collector: { type: "OTEL", interval: 300, protocol: "OTLP/HTTP", port: 4318, tls: true, telemetry: ["Traces"] },
    metrics: [{ name: "Certificate Days Remaining", metric: "ssl.certificate.days_remaining", resource: "Application", unit: "days", interval: 300, enabled: true }],
    alerts: [{ name: "Certificate Expiry", domain: "Application / Services", metric: "Certificate Days Remaining", severity: "CRITICAL", operator: "LT", threshold: 15, window: 900, consecutive: 1, notifications: ["EMAIL","PAGERDUTY"] }],
    logs: [],
  },
];

function metadata(item) {
  try {
    const value = typeof item?.connection_config === "string" ? JSON.parse(item.connection_config || "{}") : (item?.connection_config || {});
    return value.opscontrol || {};
  } catch { return {}; }
}
function collectorConfig(item) {
  try {
    return typeof item?.configuration === "string" ? JSON.parse(item.configuration || "{}") : (item?.configuration || {});
  } catch { return {}; }
}
function newDataSource(org = "") {
  return {
    organization_id: org, name: "", visible_name: "", hostname: "", environment: "PROD",
    server_type: "Application Server", os_type: "Windows", product_family: "SLM", product: "SPM",
    host_groups: ["PROD", "SLM", "Windows Servers", "Application Servers"], templates: [], description: "",
  };
}
function newCollector() {
  return { name: "", connection_mode: "DNS", ip_address: "", port: 4317, protocol: "OTLP/gRPC", tls: true, vault_secret_ref: "", telemetry: ["VM metrics", "System logs", "Application logs", "Services"] };
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
function TemplateCard({ template, selected, onClick }) {
  return <button type="button" className={selected ? "template-card selected" : "template-card"} onClick={onClick}>
    <div className="template-card-head"><div><b>{template.name}</b><small>{template.scope}</small></div><span className="template-check">{selected ? "✓" : "+"}</span></div>
    <p>{template.description}</p><div className="template-example-list">{template.examples.map(x => <span key={x}>{x}</span>)}</div>
  </button>;
}


function TemplateEditor({ template, onSave, onClose }) {
  const [draft, setDraft] = useState(JSON.parse(JSON.stringify(template)));
  const [tab, setTab] = useState("collector");
  const [newMetric, setNewMetric] = useState({ name: "", metric: "", resource: "VM", unit: "", interval: 60, enabled: true });
  const [newAlert, setNewAlert] = useState({ name: "", domain: "VM", metric: "", severity: "WARNING", operator: "GT", threshold: 80, window: 300, consecutive: 1, notifications: ["EMAIL"] });
  const [newLog, setNewLog] = useState({ name: "", source: "FILE", location: "", parser: "RAW", severity: "ERROR+", interval: 30, retention: 30, enabled: true });

  const updateCollector = (key, value) => setDraft(d => ({ ...d, collector: { ...d.collector, [key]: value } }));
  const updateRow = (section, index, key, value) => setDraft(d => ({ ...d, [section]: d[section].map((row, i) => i === index ? { ...row, [key]: value } : row) }));
  const removeRow = (section, index) => setDraft(d => ({ ...d, [section]: d[section].filter((_, i) => i !== index) }));

  const addMetric = () => {
    if (!newMetric.name.trim() || !newMetric.metric.trim()) return;
    setDraft(d => ({ ...d, metrics: [...d.metrics, { ...newMetric, interval: Number(newMetric.interval) }] }));
    setNewMetric({ name: "", metric: "", resource: "VM", unit: "", interval: 60, enabled: true });
  };
  const addAlert = () => {
    if (!newAlert.name.trim() || !newAlert.metric.trim()) return;
    setDraft(d => ({ ...d, alerts: [...d.alerts, { ...newAlert, threshold: Number(newAlert.threshold), window: Number(newAlert.window), consecutive: Number(newAlert.consecutive) }] }));
    setNewAlert({ name: "", domain: "VM", metric: "", severity: "WARNING", operator: "GT", threshold: 80, window: 300, consecutive: 1, notifications: ["EMAIL"] });
  };
  const addLog = () => {
    if (!newLog.name.trim() || !newLog.location.trim()) return;
    setDraft(d => ({ ...d, logs: [...d.logs, { ...newLog, interval: Number(newLog.interval), retention: Number(newLog.retention) }] }));
    setNewLog({ name: "", source: "FILE", location: "", parser: "RAW", severity: "ERROR+", interval: 30, retention: 30, enabled: true });
  };

  return <Modal title={template.id ? "Edit Monitoring Template" : "Create Monitoring Template"} wide onClose={onClose}>
    <div className="template-editor-title">
      <div><Field label="Template Name"><input value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} /></Field></div>
      <div><Field label="Scope"><input value={draft.scope} onChange={e => setDraft(d => ({ ...d, scope: e.target.value }))} /></Field></div>
    </div>
    <Field label="Description"><textarea value={draft.description} onChange={e => setDraft(d => ({ ...d, description: e.target.value }))} /></Field>

    <div className="template-editor-tabs">
      {[["collector","Collector configuration"],["metrics","Metric Rules"],["alerts","Alert Rules"],["logs","Log collection defaults"]].map(([key,label]) =>
        <button type="button" key={key} className={tab === key ? "template-editor-tab active" : "template-editor-tab"} onClick={() => setTab(key)}>{label}</button>
      )}
    </div>

    {tab === "collector" && <div className="template-editor-panel">
      <div className="info-box">Defaults applied when this template is attached to a Data Source. These values describe the collector package; they do not install anything by themselves.</div>
      <div className="form-grid">
        <Field label="Collector Type"><select value={draft.collector.type} onChange={e => updateCollector("type", e.target.value)}><option>OTEL</option><option>WINDOWS</option><option>LINUX</option><option>PENTAHO</option></select></Field>
        <Field label="Collection Interval (sec)"><input type="number" min="5" value={draft.collector.interval} onChange={e => updateCollector("interval", Number(e.target.value))} /></Field>
      </div>
      <div className="form-grid">
        <Field label="Protocol"><select value={draft.collector.protocol} onChange={e => updateCollector("protocol", e.target.value)}><option>OTLP/gRPC</option><option>OTLP/HTTP</option></select></Field>
        <Field label="Port"><input type="number" min="1" max="65535" value={draft.collector.port} onChange={e => updateCollector("port", Number(e.target.value))} /></Field>
      </div>
      <label className="toggle"><input type="checkbox" checked={draft.collector.tls} onChange={e => updateCollector("tls", e.target.checked)} /><span>TLS enabled by default</span></label>
      <Field label="Telemetry"><div className="check-grid">{TELEMETRY.map(x => <label className="check-option" key={x}><input type="checkbox" checked={draft.collector.telemetry.includes(x)} onChange={() => updateCollector("telemetry", draft.collector.telemetry.includes(x) ? draft.collector.telemetry.filter(v => v !== x) : [...draft.collector.telemetry, x])} /><span>{x}</span></label>)}</div></Field>
    </div>}

    {tab === "metrics" && <div className="template-editor-panel">
      <div className="template-rule-list">{draft.metrics.map((row, i) =>
        <div className="template-rule-row" key={i}><input value={row.name} placeholder="Rule name" onChange={e => updateRow("metrics", i, "name", e.target.value)} /><input value={row.metric} placeholder="Metric key" onChange={e => updateRow("metrics", i, "metric", e.target.value)} /><select value={row.resource} onChange={e => updateRow("metrics", i, "resource", e.target.value)}><option>VM</option><option>Application</option><option>ETL</option></select><input value={row.unit || ""} placeholder="Unit" onChange={e => updateRow("metrics", i, "unit", e.target.value)} /><input type="number" min="5" value={row.interval} onChange={e => updateRow("metrics", i, "interval", Number(e.target.value))} /><label className="inline-check"><input type="checkbox" checked={row.enabled} onChange={e => updateRow("metrics", i, "enabled", e.target.checked)} /> Enabled</label><button type="button" className="filter-button danger-button" onClick={() => removeRow("metrics", i)}>Remove</button></div>
      )}</div>
      <div className="template-add-row"><input value={newMetric.name} placeholder="Metric rule name" onChange={e => setNewMetric(v => ({ ...v, name: e.target.value }))} /><input value={newMetric.metric} placeholder="Metric key e.g. cpu.utilization" onChange={e => setNewMetric(v => ({ ...v, metric: e.target.value }))} /><select value={newMetric.resource} onChange={e => setNewMetric(v => ({ ...v, resource: e.target.value }))}><option>VM</option><option>Application</option><option>ETL</option></select><input value={newMetric.unit} placeholder="Unit" onChange={e => setNewMetric(v => ({ ...v, unit: e.target.value }))} /><input type="number" value={newMetric.interval} onChange={e => setNewMetric(v => ({ ...v, interval: e.target.value }))} /><button type="button" className="primary-button" onClick={addMetric}>+ Add Metric</button></div>
    </div>}

    {tab === "alerts" && <div className="template-editor-panel">
      <div className="info-box">Alert Rules are packaged by the template, but their final domain model remains intentionally separate. For now the editor supports VM, Application / Services and ETL Job rule domains.</div>
      <div className="template-rule-list">{draft.alerts.map((row, i) =>
        <div className="template-rule-card" key={i}><div className="template-rule-grid"><input value={row.name} placeholder="Alert name" onChange={e => updateRow("alerts", i, "name", e.target.value)} /><select value={row.domain} onChange={e => updateRow("alerts", i, "domain", e.target.value)}><option>VM</option><option>Application / Services</option><option>ETL</option></select><input value={row.metric} placeholder="Metric / signal" onChange={e => updateRow("alerts", i, "metric", e.target.value)} /><select value={row.severity} onChange={e => updateRow("alerts", i, "severity", e.target.value)}><option>INFO</option><option>WARNING</option><option>CRITICAL</option></select><select value={row.operator} onChange={e => updateRow("alerts", i, "operator", e.target.value)}><option>GT</option><option>GTE</option><option>LT</option><option>LTE</option><option>EQ</option><option>NE</option></select><input type="number" value={row.threshold} onChange={e => updateRow("alerts", i, "threshold", Number(e.target.value))} placeholder="Threshold" /><input type="number" value={row.window} onChange={e => updateRow("alerts", i, "window", Number(e.target.value))} placeholder="Window sec" /><input type="number" min="1" value={row.consecutive} onChange={e => updateRow("alerts", i, "consecutive", Number(e.target.value))} placeholder="Breaches" /><button type="button" className="filter-button danger-button" onClick={() => removeRow("alerts", i)}>Remove</button></div><small>Notifications: {(row.notifications || []).join(", ") || "None"}</small></div>
      )}</div>
      <div className="template-add-row alert-add-row"><input value={newAlert.name} placeholder="Alert name" onChange={e => setNewAlert(v => ({ ...v, name: e.target.value }))} /><select value={newAlert.domain} onChange={e => setNewAlert(v => ({ ...v, domain: e.target.value }))}><option>VM</option><option>Application / Services</option><option>ETL</option></select><input value={newAlert.metric} placeholder="Metric / signal" onChange={e => setNewAlert(v => ({ ...v, metric: e.target.value }))} /><select value={newAlert.severity} onChange={e => setNewAlert(v => ({ ...v, severity: e.target.value }))}><option>WARNING</option><option>CRITICAL</option><option>INFO</option></select><select value={newAlert.operator} onChange={e => setNewAlert(v => ({ ...v, operator: e.target.value }))}><option>GT</option><option>GTE</option><option>LT</option><option>LTE</option></select><input type="number" value={newAlert.threshold} onChange={e => setNewAlert(v => ({ ...v, threshold: e.target.value }))} /><button type="button" className="primary-button" onClick={addAlert}>+ Add Alert</button></div>
    </div>}

    {tab === "logs" && <div className="template-editor-panel">
      <div className="template-rule-list">{draft.logs.map((row, i) =>
        <div className="template-rule-card" key={i}><div className="template-rule-grid"><input value={row.name} placeholder="Log source name" onChange={e => updateRow("logs", i, "name", e.target.value)} /><select value={row.source} onChange={e => updateRow("logs", i, "source", e.target.value)}><option>FILE</option><option>WINDOWS_EVENT</option><option>JOURNALD</option><option>API</option></select><input value={row.location} placeholder="Path / source" onChange={e => updateRow("logs", i, "location", e.target.value)} /><select value={row.parser} onChange={e => updateRow("logs", i, "parser", e.target.value)}><option>RAW</option><option>SYSLOG</option><option>WINDOWS_EVENT</option><option>PENTAHO</option><option>TEXT</option></select><input value={row.severity} placeholder="Severity" onChange={e => updateRow("logs", i, "severity", e.target.value)} /><input type="number" value={row.interval} onChange={e => updateRow("logs", i, "interval", Number(e.target.value))} placeholder="Interval" /><input type="number" value={row.retention} onChange={e => updateRow("logs", i, "retention", Number(e.target.value))} placeholder="Days" /><label className="inline-check"><input type="checkbox" checked={row.enabled} onChange={e => updateRow("logs", i, "enabled", e.target.checked)} /> Enabled</label><button type="button" className="filter-button danger-button" onClick={() => removeRow("logs", i)}>Remove</button></div></div>
      )}</div>
      <div className="template-add-row"><input value={newLog.name} placeholder="Log source name" onChange={e => setNewLog(v => ({ ...v, name: e.target.value }))} /><select value={newLog.source} onChange={e => setNewLog(v => ({ ...v, source: e.target.value }))}><option>FILE</option><option>WINDOWS_EVENT</option><option>JOURNALD</option><option>API</option></select><input value={newLog.location} placeholder="Path / source" onChange={e => setNewLog(v => ({ ...v, location: e.target.value }))} /><select value={newLog.parser} onChange={e => setNewLog(v => ({ ...v, parser: e.target.value }))}><option>RAW</option><option>SYSLOG</option><option>WINDOWS_EVENT</option><option>PENTAHO</option><option>TEXT</option></select><button type="button" className="primary-button" onClick={addLog}>+ Add Log Source</button></div>
    </div>}

    <div className="form-footer"><span className="muted small">Template package: collector + metrics + alerts + logs</span><div><button type="button" className="filter-button" onClick={onClose}>Cancel</button><button type="button" className="primary-button" onClick={() => onSave(draft)}>Save Template</button></div></div>
  </Modal>;
}

export default function ResourceManagement({ organizationId, organizationIds = [] }) {
  const scope = organizationIds.length ? organizationIds : (organizationId ? [organizationId] : []);
  const [tab, setTab] = useState("data-sources");
  const [organizations, setOrganizations] = useState([]);
  const [dataSources, setDataSources] = useState([]);
  const [collectors, setCollectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [wizard, setWizard] = useState(false);
  const [step, setStep] = useState(1);
  const [ds, setDs] = useState(newDataSource(scope[0] || ""));
  const [collector, setCollector] = useState(newCollector());
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(null);
  const [templates, setTemplates] = useState(() => {
    try {
      const saved = JSON.parse(window.localStorage.getItem("opscontrol.monitoringTemplates") || "null");
      return Array.isArray(saved) && saved.length ? saved : DEFAULT_TEMPLATES;
    } catch { return DEFAULT_TEMPLATES; }
  });
  const [templateEditor, setTemplateEditor] = useState(null);

  const reload = async () => {
    setLoading(true); setError(null);
    try {
      const orgs = await fetchOrganizations();
      setOrganizations(orgs);
      const ids = scope.length ? scope : orgs.map(x => x.id);
      const lists = ids.length ? await Promise.all(ids.map(id => fetchDataSources({ organization_id: id }))) : [await fetchDataSources()];
      setDataSources([...new Map(lists.flat().map(x => [x.id, x])).values()]);
      setCollectors(await fetchCollectors());
    } catch (e) { setError(e.message || "Unable to load resource management"); }
    finally { setLoading(false); }
  };
  useEffect(() => { reload(); }, [organizationId, JSON.stringify(organizationIds)]);
  useEffect(() => {
    window.localStorage.setItem("opscontrol.monitoringTemplates", JSON.stringify(templates));
  }, [templates]);

  const orgMap = useMemo(() => new Map(organizations.map(x => [x.id, x])), [organizations]);
  const sources = useMemo(() => {
    const q = query.toLowerCase().trim();
    return dataSources.filter(x => {
      const m = metadata(x);
      return !q || [x.name, x.endpoint, m.visible_name, m.hostname, m.environment, m.product, m.product_family, ...(m.host_groups || [])].join(" ").toLowerCase().includes(q);
    });
  }, [dataSources, query]);
  const collectorRows = useMemo(() => {
    const q = query.toLowerCase().trim();
    return collectors.filter(x => !q || [x.name, x.collector_type, dataSources.find(s => s.id === x.data_source_id)?.name].join(" ").toLowerCase().includes(q));
  }, [collectors, dataSources, query]);

  const openWizard = () => {
    setStep(1); setDs(newDataSource(scope[0] || organizations[0]?.id || "")); setCollector(newCollector()); setWizard(true);
  };
  const toggle = (field, value) => setDs(f => ({ ...f, [field]: f[field].includes(value) ? f[field].filter(x => x !== value) : [...f[field], value] }));
  const toggleTelemetry = value => setCollector(f => ({ ...f, telemetry: f.telemetry.includes(value) ? f.telemetry.filter(x => x !== value) : [...f.telemetry, value] }));

  const createResource = async () => {
    setSaving(true); setError(null);
    try {
      const chosen = templates.filter(x => ds.templates.includes(x.id));
      const source = await createDataSource({
        organization_id: ds.organization_id,
        name: ds.name || ds.hostname,
        source_type: ds.os_type.toUpperCase(),
        description: ds.description || null,
        endpoint: ds.hostname,
        auth_type: "PTC_VAULT",
        connection_config: { opscontrol: {
          visible_name: ds.visible_name || ds.name || ds.hostname, hostname: ds.hostname, environment: ds.environment,
          server_type: ds.server_type, os_type: ds.os_type, product_family: ds.product_family, product: ds.product,
          host_groups: ds.host_groups, template_ids: ds.templates, templates: chosen.map(x => x.name),
        }},
        enabled: true,
      });
      await createCollector({
        data_source_id: source.id, name: collector.name || `${ds.hostname || ds.name}-OTEL`,
        collector_type: "OTEL", enabled: true, interval_seconds: 30,
        configuration: {
          provider: "opentelemetry",
          connection: { mode: collector.connection_mode, ip_address: collector.ip_address, dns_name: ds.hostname, port: Number(collector.port), protocol: collector.protocol, tls: collector.tls },
          credential_provider: "PTC_VAULT", vault_secret_ref: collector.vault_secret_ref || null,
          telemetry: collector.telemetry, template_ids: ds.templates,
        },
      });
      setWizard(false); setTab("data-sources"); await reload();
    } catch (e) { setError(e.message || "Unable to create Data Source and Collector"); }
    finally { setSaving(false); }
  };

  const openEdit = source => {
    const m = metadata(source);
    setEditing(source);
    setDs({
      organization_id: source.organization_id, name: source.name || "", visible_name: m.visible_name || source.name || "",
      hostname: m.hostname || source.endpoint || "", environment: m.environment || "PROD", server_type: m.server_type || "Application Server",
      os_type: m.os_type || "Windows", product_family: m.product_family || "SLM", product: m.product || "SPM",
      host_groups: m.host_groups || [], templates: m.template_ids || [], description: source.description || "",
    });
  };
  const saveEdit = async e => {
    e.preventDefault(); setSaving(true);
    try {
      const old = metadata(editing);
      await updateDataSource(editing.id, {
        name: ds.name, endpoint: ds.hostname, description: ds.description || null,
        connection_config: { ...(editing.connection_config || {}), opscontrol: {
          ...old, visible_name: ds.visible_name || ds.name, hostname: ds.hostname, environment: ds.environment,
          server_type: ds.server_type, os_type: ds.os_type, product_family: ds.product_family, product: ds.product,
          host_groups: ds.host_groups, template_ids: ds.templates, templates: templates.filter(x => ds.templates.includes(x.id)).map(x => x.name),
        }},
      });
      setEditing(null); await reload();
    } catch (e) { setError(e.message || "Unable to update Data Source"); }
    finally { setSaving(false); }
  };

  const orgName = id => orgMap.get(id)?.name || "—";
  const sourceCollectorCount = id => collectors.filter(x => x.data_source_id === id).length;

  return <div className="resource-page">
    <div className="page-heading">
      <div><h1>Resource Management</h1><p>Simple customer onboarding: Organization → Data Source → Collector → Templates.</p></div>
      <div className="heading-actions"><button className="filter-button" onClick={reload}>Refresh</button><button className="primary-button" onClick={openWizard} disabled={!organizations.length}>+ Add Data Source</button></div>
    </div>

    <div className="resource-summary-grid">
      <div className="card resource-summary-card"><span>Organizations</span><b>{organizations.length}</b><small>Customer boundaries</small></div>
      <div className="card resource-summary-card"><span>Data Sources</span><b>{dataSources.length}</b><small>Customer machines</small></div>
      <div className="card resource-summary-card"><span>Collectors</span><b>{collectors.length}</b><small>{collectors.filter(x => String(x.status).toUpperCase() === "ONLINE").length} online</small></div>
      <div className="card resource-summary-card"><span>Templates</span><b>{templates.length}</b><small>Reusable packages</small></div>
    </div>

    <div className="resource-layout">
      <aside className="resource-sidebar card">{NAV.map(([key, title, subtitle]) =>
        <button key={key} className={tab === key ? "resource-tab active" : "resource-tab"} onClick={() => { setTab(key); setQuery(""); }}><b>{title}</b><small>{subtitle}</small></button>
      )}</aside>

      <section className="resource-main">
        {error && <div className="scope-banner error-banner">{error}</div>}

        {tab === "organizations" && <div className="resource-section-stack">
          <div className="card resource-toolbar"><div><h2>Organizations</h2><span className="muted small">Customers are the top-level ownership boundary.</span></div><span className="resource-readonly-badge">Provisioning next</span></div>
          <div className="organization-grid">{organizations.map(org =>
            <div className="card organization-card" key={org.id}>
              <div className="organization-card-head"><div><b>{org.name}</b><small>{org.code}</small></div><span className={org.active ? "status status--success" : "status status--unknown"}>{org.active ? "ACTIVE" : "INACTIVE"}</span></div>
              <div className="organization-fields"><div><span>Services</span><b>SLM / API</b></div><div><span>Distributed List</span><b>Customer profile</b></div><div><span>ServiceNow</span><b>Customer integration</b></div></div>
            </div>
          )}</div>
          <div className="card info-box resource-info-panel"><b>Organization model</b><p>Organization configuration will own customer services, ServiceNow endpoint, distributed lists and application catalog. The current backend exposes organizations as read-only, so this phase does not invent a create/update API.</p></div>
        </div>}

        {tab === "data-sources" && <div className="resource-section-stack">
          <div className="card resource-toolbar"><div><h2>Data Sources</h2><span className="muted small">Zabbix-inspired host identity, modernized for OpsControl.</span></div><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search hostname, product, group..." /></div>
          {loading ? <div className="card state-panel"><div className="spinner" /><h3>Loading resources</h3></div> : sources.length === 0 ? <div className="card state-panel"><h3>No Data Sources</h3><p>Start with a customer machine and choose one or more Monitoring Templates.</p><button className="primary-button" onClick={openWizard}>+ Add Data Source</button></div> :
            <div className="card table-wrap"><table><thead><tr><th>Data Source</th><th>Organization</th><th>Environment</th><th>Server / OS</th><th>Product</th><th>Templates</th><th>Collector</th><th /></tr></thead><tbody>
              {sources.map(source => { const m = metadata(source); const cs = collectors.filter(c => c.data_source_id === source.id); return <tr key={source.id}>
                <td><b>{m.visible_name || source.name}</b><small>{m.hostname || source.endpoint || "No hostname"} · {source.name}</small></td>
                <td>{orgName(source.organization_id)}</td><td><span className="status status--running">{m.environment || "—"}</span></td>
                <td>{m.server_type || "—"}<small>{m.os_type || "—"}</small></td><td>{m.product || "—"}<small>{m.product_family || "—"}</small></td>
                <td><div className="chip-row">{(m.templates || []).slice(0, 2).map(x => <span className="mini-chip" key={x}>{x}</span>)}{(m.templates || []).length > 2 && <span className="mini-chip">+{m.templates.length - 2}</span>}</div></td>
                <td>{cs.length ? <span className={String(cs[0].status).toUpperCase() === "ONLINE" ? "status status--success" : "status status--unknown"}>{cs[0].status || "STOPPED"}</span> : <span className="status status--unknown">NOT INSTALLED</span>}</td>
                <td><button className="filter-button" onClick={() => openEdit(source)}>Edit</button></td>
              </tr>; })}
            </tbody></table></div>}
        </div>}

        {tab === "collectors" && <div className="resource-section-stack">
          <div className="card resource-toolbar"><div><h2>Collectors</h2><span className="muted small">One OTEL collector per Data Source for metrics, logs and traces.</span></div><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search collector or Data Source..." /></div>
          {loading ? <div className="card state-panel"><div className="spinner" /><h3>Loading collectors</h3></div> : collectorRows.length === 0 ? <div className="card state-panel"><h3>No Collectors</h3><p>Create a Data Source to onboard its collector.</p></div> :
            <div className="card table-wrap"><table><thead><tr><th>Collector</th><th>Data Source</th><th>Type</th><th>Telemetry</th><th>Status</th><th>Last Run</th></tr></thead><tbody>
              {collectorRows.map(item => { const c = collectorConfig(item); const source = dataSources.find(s => s.id === item.data_source_id); const m = metadata(source); return <tr key={item.id}>
                <td><b>{item.name}</b><small>{c.connection?.protocol || "OTLP"}</small></td><td>{m.visible_name || source?.name || "—"}<small>{m.hostname || source?.endpoint || ""}</small></td><td>{item.collector_type}</td>
                <td><div className="chip-row">{(c.telemetry || []).slice(0, 3).map(x => <span className="mini-chip" key={x}>{x}</span>)}</div></td><td><span className={String(item.status).toUpperCase() === "ONLINE" ? "status status--success" : "status status--unknown"}>{item.status || "STOPPED"}</span></td><td>{item.last_run_at ? new Date(item.last_run_at).toLocaleString("en-IN") : "Never"}</td>
              </tr>; })}
            </tbody></table></div>}
        </div>}

        {tab === "templates" && <div className="resource-section-stack">
          <div className="card resource-toolbar">
            <div><h2>Monitoring Templates</h2><span className="muted small">Build reusable monitoring packages once, then apply them to hundreds of Data Sources.</span></div>
            <button className="primary-button" onClick={() => setTemplateEditor({ id: "", name: "New Monitoring Template", description: "", scope: "VM + Application / Services", collector: { type: "OTEL", interval: 30, protocol: "OTLP/gRPC", port: 4317, tls: true, telemetry: ["VM metrics"] }, metrics: [], alerts: [], logs: [] })}>+ Create Template</button>
          </div>
          <div className="template-admin-grid">
            {templates.map(t => <div className="card template-admin-card" key={t.id}>
              <div className="template-admin-head"><div><b>{t.name}</b><small>{t.scope}</small></div><button className="filter-button" onClick={() => setTemplateEditor(t)}>Edit</button></div>
              <p>{t.description}</p>
              <div className="template-counts"><span>{t.collector?.telemetry?.length || 0} collector signals</span><span>{t.metrics?.length || 0} metric rules</span><span>{t.alerts?.length || 0} alert rules</span><span>{t.logs?.length || 0} log defaults</span></div>
            </div>)}
          </div>
          <div className="card info-box resource-info-panel"><b>Template package model</b><p>Each template is a complete monitoring package: Collector configuration + Metric Rules + Alert Rules + Log collection defaults. Templates are independent from the eventual Alert Rule domain design.</p></div>
        </div>

      </section>
    </div>

    {wizard && <Modal title="Add Data Source" wide onClose={() => !saving && setWizard(false)}>
      <div className="onboarding-steps">{["Data Source", "Templates", "Collector", "Review"].map((x, i) => <div key={x} className={step === i + 1 ? "onboarding-step active" : step > i + 1 ? "onboarding-step complete" : "onboarding-step"}><span>{step > i + 1 ? "✓" : i + 1}</span>{x}</div>)}</div>

      {step === 1 && <div className="resource-form">
        <div className="info-box">Configure the machine first. Organization, environment, product and host groups become the Data Source identity.</div>
        <div className="form-grid"><Field label="Organization"><select value={ds.organization_id} onChange={e => setDs(f => ({ ...f, organization_id: e.target.value }))}>{organizations.map(x => <option key={x.id} value={x.id}>{x.name} ({x.code})</option>)}</select></Field><Field label="Environment"><select value={ds.environment} onChange={e => setDs(f => ({ ...f, environment: e.target.value }))}>{ENVIRONMENTS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <div className="form-grid"><Field label="Host Name"><input required value={ds.hostname} onChange={e => setDs(f => ({ ...f, hostname: e.target.value, name: f.name || e.target.value }))} placeholder="HPPR-Prodapp001" /></Field><Field label="Visible Name"><input value={ds.visible_name} onChange={e => setDs(f => ({ ...f, visible_name: e.target.value }))} placeholder="Rivian Prod APP" /></Field></div>
        <div className="form-grid"><Field label="Server Type"><select value={ds.server_type} onChange={e => setDs(f => ({ ...f, server_type: e.target.value }))}>{SERVER_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="OS Type"><select value={ds.os_type} onChange={e => setDs(f => ({ ...f, os_type: e.target.value }))}>{OS_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <div className="form-grid"><Field label="Product Family"><select value={ds.product_family} onChange={e => setDs(f => ({ ...f, product_family: e.target.value }))}><option>SLM</option></select></Field><Field label="Product"><select value={ds.product} onChange={e => setDs(f => ({ ...f, product: e.target.value }))}>{PRODUCTS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <Field label="Host Groups" help="Structured fields remain authoritative; groups provide flexible NOC filtering."><div className="check-grid">{HOST_GROUPS.map(x => <label className="check-option" key={x}><input type="checkbox" checked={ds.host_groups.includes(x)} onChange={() => toggle("host_groups", x)} /><span>{x}</span></label>)}</div></Field>
        <Field label="Description"><textarea value={ds.description} onChange={e => setDs(f => ({ ...f, description: e.target.value }))} placeholder="Production application server" /></Field>
        <div className="form-footer"><span className="muted small">Step 1 of 4</span><button type="button" className="primary-button" disabled={!ds.organization_id || !ds.hostname} onClick={() => setStep(2)}>Next: Templates →</button></div>
      </div>}

      {step === 2 && <div className="resource-form">
        <div className="info-box">Select reusable packages instead of manually configuring hundreds of servers. Multiple templates can be attached to one Data Source.</div>
        <div className="template-grid">{DEFAULT_TEMPLATES.map(t => <TemplateCard key={t.id} template={t} selected={ds.templates.includes(t.id)} onClick={() => toggle("templates", t.id)} />)}</div>
        <div className="form-footer"><span className="muted small">Step 2 of 4 · {ds.templates.length} selected</span><div><button type="button" className="filter-button" onClick={() => setStep(1)}>← Back</button><button type="button" className="primary-button" onClick={() => setStep(3)}>Next: Collector →</button></div></div>
      </div>}

      {step === 3 && <div className="resource-form">
        <div className="info-box"><b>OTEL Collector</b> is the single collection agent for the Data Source. It can carry metrics, logs and traces. Credentials are references to the PTC Vault; passwords are never entered into OpsControl.</div>
        <Field label="Collector Name"><input value={collector.name} onChange={e => setCollector(f => ({ ...f, name: e.target.value }))} placeholder={`${ds.hostname || ds.name}-OTEL`} /></Field>
        <div className="form-grid"><Field label="Connection Mode"><select value={collector.connection_mode} onChange={e => setCollector(f => ({ ...f, connection_mode: e.target.value }))}><option>DNS</option><option>IP</option></select></Field><Field label="Port"><input type="number" min="1" max="65535" value={collector.port} onChange={e => setCollector(f => ({ ...f, port: Number(e.target.value) }))} /></Field></div>
        <div className="form-grid"><Field label="IP Address" help="Used when IP mode is selected."><input value={collector.ip_address} onChange={e => setCollector(f => ({ ...f, ip_address: e.target.value }))} placeholder="10.10.10.25" /></Field><Field label="Protocol"><select value={collector.protocol} onChange={e => setCollector(f => ({ ...f, protocol: e.target.value }))}><option>OTLP/gRPC</option><option>OTLP/HTTP</option></select></Field></div>
        <Field label="PTC Vault Secret Reference" help="Reference only; secret value is never stored in OpsControl."><input value={collector.vault_secret_ref} onChange={e => setCollector(f => ({ ...f, vault_secret_ref: e.target.value }))} placeholder="ptc/prod/rivian/hppr-prodapp001" /></Field>
        <Field label="Telemetry"><div className="check-grid">{TELEMETRY.map(x => <label className="check-option" key={x}><input type="checkbox" checked={collector.telemetry.includes(x)} onChange={() => toggleTelemetry(x)} /><span>{x}</span></label>)}</div></Field>
        <label className="toggle"><input type="checkbox" checked={collector.tls} onChange={e => setCollector(f => ({ ...f, tls: e.target.checked }))} /><span>TLS enabled</span></label>
        <div className="form-footer"><span className="muted small">Step 3 of 4</span><div><button type="button" className="filter-button" onClick={() => setStep(2)}>← Back</button><button type="button" className="primary-button" onClick={() => setStep(4)}>Review →</button></div></div>
      </div>}

      {step === 4 && <div className="resource-form">
        <div className="review-grid"><div className="card review-card"><span>Organization</span><b>{orgName(ds.organization_id)}</b><small>{ds.environment} · {ds.product_family} · {ds.product}</small></div><div className="card review-card"><span>Data Source</span><b>{ds.visible_name || ds.name}</b><small>{ds.hostname} · {ds.os_type} · {ds.server_type}</small></div><div className="card review-card"><span>Templates</span><b>{ds.templates.length || "None"}</b><small>{DEFAULT_TEMPLATES.filter(x => ds.templates.includes(x.id)).map(x => x.name).join(", ") || "No template selected"}</small></div><div className="card review-card"><span>Collector</span><b>{collector.name || `${ds.hostname || ds.name}-OTEL`}</b><small>{collector.protocol} · {collector.port} · PTC Vault</small></div></div>
        <div className="card source-fact"><b>What happens next</b><p>OpsControl creates the Data Source and one OTEL Collector. Selected templates are attached as reusable monitoring packages. Metric and Alert Rule backends are deliberately unchanged in this phase.</p></div>
        <div className="form-footer"><span className="muted small">Step 4 of 4</span><div><button type="button" className="filter-button" onClick={() => setStep(3)}>← Back</button><button type="button" className="primary-button" disabled={saving} onClick={createResource}>{saving ? "Creating..." : "Create Data Source + Collector"}</button></div></div>
      </div>}
    </Modal>}

    {templateEditor && <TemplateEditor
      template={templateEditor}
      onClose={() => setTemplateEditor(null)}
      onSave={draft => {
        const id = draft.id || draft.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "") || `template-${Date.now()}`;
        const next = { ...draft, id };
        setTemplates(current => current.some(x => x.id === id) ? current.map(x => x.id === id ? next : x) : [...current, next]);
        setTemplateEditor(null);
      }}
    />}

    {editing && <Modal title={`${ds.visible_name || ds.name}`} onClose={() => !saving && setEditing(null)}>
      <form className="resource-form" onSubmit={async e => {
        e.preventDefault(); setSaving(true);
        try {
          const old = metadata(editing);
          await updateDataSource(editing.id, { name: ds.name, endpoint: ds.hostname, description: ds.description || null, connection_config: { ...(editing.connection_config || {}), opscontrol: { ...old, visible_name: ds.visible_name || ds.name, hostname: ds.hostname, environment: ds.environment, server_type: ds.server_type, os_type: ds.os_type, product_family: ds.product_family, product: ds.product, host_groups: ds.host_groups, template_ids: ds.templates, templates: DEFAULT_TEMPLATES.filter(x => ds.templates.includes(x.id)).map(x => x.name) } } });
          setEditing(null); await reload();
        } catch (e2) { setError(e2.message || "Unable to update Data Source"); } finally { setSaving(false); }
      }}>
        <div className="info-box">Zabbix-inspired host editing, but with OpsControl terminology and template packages.</div>
        <div className="form-grid"><Field label="Host Name"><input required value={ds.hostname} onChange={e => setDs(f => ({ ...f, hostname: e.target.value }))} /></Field><Field label="Visible Name"><input value={ds.visible_name} onChange={e => setDs(f => ({ ...f, visible_name: e.target.value }))} /></Field></div>
        <div className="form-grid"><Field label="Environment"><select value={ds.environment} onChange={e => setDs(f => ({ ...f, environment: e.target.value }))}>{ENVIRONMENTS.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Server Type"><select value={ds.server_type} onChange={e => setDs(f => ({ ...f, server_type: e.target.value }))}>{SERVER_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <div className="form-grid"><Field label="OS Type"><select value={ds.os_type} onChange={e => setDs(f => ({ ...f, os_type: e.target.value }))}>{OS_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Product"><select value={ds.product} onChange={e => setDs(f => ({ ...f, product: e.target.value }))}>{PRODUCTS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <Field label="Host Groups"><div className="check-grid">{HOST_GROUPS.map(x => <label className="check-option" key={x}><input type="checkbox" checked={ds.host_groups.includes(x)} onChange={() => toggle("host_groups", x)} /><span>{x}</span></label>)}</div></Field>
        <Field label="Templates"><div className="template-grid">{DEFAULT_TEMPLATES.map(t => <TemplateCard key={t.id} template={t} selected={ds.templates.includes(t.id)} onClick={() => toggle("templates", t.id)} />)}</div></Field>
        <Field label="Description"><textarea value={ds.description} onChange={e => setDs(f => ({ ...f, description: e.target.value }))} /></Field>
        <div className="form-footer"><span className="muted small">Templates are stored with the Data Source configuration.</span><div><button type="button" className="filter-button" onClick={() => setEditing(null)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button></div></div>
      </form>
    </Modal>}
  </div>;
}
