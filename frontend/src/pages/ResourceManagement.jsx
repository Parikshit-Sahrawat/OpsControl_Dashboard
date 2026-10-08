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

const TEMPLATES = [
  { id: "windows-application", name: "Windows Application Server", scope: "VM + Application / Services", description: "Windows infrastructure, services, application logs and standard health checks.", examples: ["CPU", "Memory", "Disk", "Windows Services", "Event Logs"] },
  { id: "linux-database", name: "Linux Database Server", scope: "VM + Application / Services", description: "Linux host telemetry with database/application log collection defaults.", examples: ["CPU", "Memory", "Disk", "Processes", "Database logs"] },
  { id: "pentaho-server", name: "Pentaho Server", scope: "VM + ETL", description: "ETL-oriented defaults for Pentaho/Kettle and batch job telemetry.", examples: ["CPU", "Disk", "Pentaho logs", "Job execution", "Batch runtime"] },
  { id: "web-ui", name: "SLM Web UI", scope: "Application / Services", description: "WebUI/Tomcat/Apache monitoring defaults for SLM application servers.", examples: ["Apache", "Tomcat", "HTTP health", "Response time"] },
  { id: "ssl", name: "SSL / Certificate", scope: "Application / Services", description: "Certificate and TLS monitoring defaults for customer endpoints.", examples: ["Certificate expiry", "TLS validity", "Endpoint availability"] },
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
      const chosen = TEMPLATES.filter(x => ds.templates.includes(x.id));
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
        data_source_id: source.id, name: collector.name || ${ds.hostname || ds.name}-OTEL,
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
          host_groups: ds.host_groups, template_ids: ds.templates, templates: TEMPLATES.filter(x => ds.templates.includes(x.id)).map(x => x.name),
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
      <div className="card resource-summary-card"><span>Templates</span><b>{TEMPLATES.length}</b><small>Reusable packages</small></div>
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
          <div className="card resource-toolbar"><div><h2>Monitoring Templates</h2><span className="muted small">Each package can contain collector configuration, metrics, alerts and log collection defaults.</span></div></div>
          <div className="template-grid">{TEMPLATES.map(t => <TemplateCard key={t.id} template={t} selected={false} onClick={() => {}} />)}</div>
          <div className="card info-box resource-info-panel"><b>Template rule</b><p>Templates are not alert rules. They are reusable monitoring packages selected during Data Source onboarding. Metric Rules and the three Alert Rule domains will be designed later.</p></div>
        </div>}
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
        <div className="template-grid">{TEMPLATES.map(t => <TemplateCard key={t.id} template={t} selected={ds.templates.includes(t.id)} onClick={() => toggle("templates", t.id)} />)}</div>
        <div className="form-footer"><span className="muted small">Step 2 of 4 · {ds.templates.length} selected</span><div><button type="button" className="filter-button" onClick={() => setStep(1)}>← Back</button><button type="button" className="primary-button" onClick={() => setStep(3)}>Next: Collector →</button></div></div>
      </div>}

      {step === 3 && <div className="resource-form">
        <div className="info-box"><b>OTEL Collector</b> is the single collection agent for the Data Source. It can carry metrics, logs and traces. Credentials are references to the PTC Vault; passwords are never entered into OpsControl.</div>
        <Field label="Collector Name"><input value={collector.name} onChange={e => setCollector(f => ({ ...f, name: e.target.value }))} placeholder={${ds.hostname || ds.name}-OTEL} /></Field>
        <div className="form-grid"><Field label="Connection Mode"><select value={collector.connection_mode} onChange={e => setCollector(f => ({ ...f, connection_mode: e.target.value }))}><option>DNS</option><option>IP</option></select></Field><Field label="Port"><input type="number" min="1" max="65535" value={collector.port} onChange={e => setCollector(f => ({ ...f, port: Number(e.target.value) }))} /></Field></div>
        <div className="form-grid"><Field label="IP Address" help="Used when IP mode is selected."><input value={collector.ip_address} onChange={e => setCollector(f => ({ ...f, ip_address: e.target.value }))} placeholder="10.10.10.25" /></Field><Field label="Protocol"><select value={collector.protocol} onChange={e => setCollector(f => ({ ...f, protocol: e.target.value }))}><option>OTLP/gRPC</option><option>OTLP/HTTP</option></select></Field></div>
        <Field label="PTC Vault Secret Reference" help="Reference only; secret value is never stored in OpsControl."><input value={collector.vault_secret_ref} onChange={e => setCollector(f => ({ ...f, vault_secret_ref: e.target.value }))} placeholder="ptc/prod/rivian/hppr-prodapp001" /></Field>
        <Field label="Telemetry"><div className="check-grid">{TELEMETRY.map(x => <label className="check-option" key={x}><input type="checkbox" checked={collector.telemetry.includes(x)} onChange={() => toggleTelemetry(x)} /><span>{x}</span></label>)}</div></Field>
        <label className="toggle"><input type="checkbox" checked={collector.tls} onChange={e => setCollector(f => ({ ...f, tls: e.target.checked }))} /><span>TLS enabled</span></label>
        <div className="form-footer"><span className="muted small">Step 3 of 4</span><div><button type="button" className="filter-button" onClick={() => setStep(2)}>← Back</button><button type="button" className="primary-button" onClick={() => setStep(4)}>Review →</button></div></div>
      </div>}

      {step === 4 && <div className="resource-form">
        <div className="review-grid"><div className="card review-card"><span>Organization</span><b>{orgName(ds.organization_id)}</b><small>{ds.environment} · {ds.product_family} · {ds.product}</small></div><div className="card review-card"><span>Data Source</span><b>{ds.visible_name || ds.name}</b><small>{ds.hostname} · {ds.os_type} · {ds.server_type}</small></div><div className="card review-card"><span>Templates</span><b>{ds.templates.length || "None"}</b><small>{TEMPLATES.filter(x => ds.templates.includes(x.id)).map(x => x.name).join(", ") || "No template selected"}</small></div><div className="card review-card"><span>Collector</span><b>{collector.name || ${ds.hostname || ds.name}-OTEL}</b><small>{collector.protocol} · {collector.port} · PTC Vault</small></div></div>
        <div className="card source-fact"><b>What happens next</b><p>OpsControl creates the Data Source and one OTEL Collector. Selected templates are attached as reusable monitoring packages. Metric and Alert Rule backends are deliberately unchanged in this phase.</p></div>
        <div className="form-footer"><span className="muted small">Step 4 of 4</span><div><button type="button" className="filter-button" onClick={() => setStep(3)}>← Back</button><button type="button" className="primary-button" disabled={saving} onClick={createResource}>{saving ? "Creating..." : "Create Data Source + Collector"}</button></div></div>
      </div>}
    </Modal>}

    {editing && <Modal title={${ds.visible_name || ds.name}} onClose={() => !saving && setEditing(null)}>
      <form className="resource-form" onSubmit={async e => {
        e.preventDefault(); setSaving(true);
        try {
          const old = metadata(editing);
          await updateDataSource(editing.id, { name: ds.name, endpoint: ds.hostname, description: ds.description || null, connection_config: { ...(editing.connection_config || {}), opscontrol: { ...old, visible_name: ds.visible_name || ds.name, hostname: ds.hostname, environment: ds.environment, server_type: ds.server_type, os_type: ds.os_type, product_family: ds.product_family, product: ds.product, host_groups: ds.host_groups, template_ids: ds.templates, templates: TEMPLATES.filter(x => ds.templates.includes(x.id)).map(x => x.name) } } });
          setEditing(null); await reload();
        } catch (e2) { setError(e2.message || "Unable to update Data Source"); } finally { setSaving(false); }
      }}>
        <div className="info-box">Zabbix-inspired host editing, but with OpsControl terminology and template packages.</div>
        <div className="form-grid"><Field label="Host Name"><input required value={ds.hostname} onChange={e => setDs(f => ({ ...f, hostname: e.target.value }))} /></Field><Field label="Visible Name"><input value={ds.visible_name} onChange={e => setDs(f => ({ ...f, visible_name: e.target.value }))} /></Field></div>
        <div className="form-grid"><Field label="Environment"><select value={ds.environment} onChange={e => setDs(f => ({ ...f, environment: e.target.value }))}>{ENVIRONMENTS.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Server Type"><select value={ds.server_type} onChange={e => setDs(f => ({ ...f, server_type: e.target.value }))}>{SERVER_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <div className="form-grid"><Field label="OS Type"><select value={ds.os_type} onChange={e => setDs(f => ({ ...f, os_type: e.target.value }))}>{OS_TYPES.map(x => <option key={x}>{x}</option>)}</select></Field><Field label="Product"><select value={ds.product} onChange={e => setDs(f => ({ ...f, product: e.target.value }))}>{PRODUCTS.map(x => <option key={x}>{x}</option>)}</select></Field></div>
        <Field label="Host Groups"><div className="check-grid">{HOST_GROUPS.map(x => <label className="check-option" key={x}><input type="checkbox" checked={ds.host_groups.includes(x)} onChange={() => toggle("host_groups", x)} /><span>{x}</span></label>)}</div></Field>
        <Field label="Templates"><div className="template-grid">{TEMPLATES.map(t => <TemplateCard key={t.id} template={t} selected={ds.templates.includes(t.id)} onClick={() => toggle("templates", t.id)} />)}</div></Field>
        <Field label="Description"><textarea value={ds.description} onChange={e => setDs(f => ({ ...f, description: e.target.value }))} /></Field>
        <div className="form-footer"><span className="muted small">Templates are stored with the Data Source configuration.</span><div><button type="button" className="filter-button" onClick={() => setEditing(null)}>Cancel</button><button className="primary-button" disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button></div></div>
      </form>
    </Modal>}
  </div>;
}
