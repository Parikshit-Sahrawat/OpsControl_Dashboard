import { setAdministrativeCustomers } from "../auth";
import { useEffect, useRef, useState } from "react";
import { control, control as scopedControl, downloadPackage } from "../controlPlane";
import { hasPermission } from "../permissions";
import { canOpenSection } from "../navigation";
import { fetchAuthorizedCustomers } from "../api";
import useDialogFocus from "../components/useDialogFocus";
import DataPipelineIntegrations from "./DataPipelineIntegrations";
import ImportedDiscoveryInventory from "../components/ImportedDiscoveryInventory";
import MonitoringSetup from "./MonitoringSetup";
import EventDelivery from "./EventDelivery";
import DynamicConfigurationForm from "../components/DynamicConfigurationForm";
import CollectorControl from "./CollectorControl";
import ResourceManagementV2 from "./ResourceManagementV2";
import DomainParameters, { Field } from "./DomainParameters";
const base = "/api/v1/unified";
const domainNames = {
  ETL: "Data Pipelines",
  VM: "Compute Instances",
  API: "API Endpoints",
};
const parameterNames = {
  ETL: "Data Pipeline Parameters",
  VM: "Compute Health Parameters",
  API: "API Endpoint Parameters",
};
const alertNames = {
  VM: "Compute Instances Alert Setup",
  ETL: "Data Pipelines Alert Setup",
  API: "API Endpoints Alert Setup",
};
const blank = (domain) => ({
  name: "",
  organization_id: "",
  new_customer: null,
  environment: "PROD",
  description: "",
  tags: {},
  active: true,
  ...(domain === "VM"
    ? {
        hostname: "",
        address: "",
        os_type: "Linux",
        vm_type: "VM",
        deployment_type: "PRIVATE_CLOUD",
        native_os_metrics: true,
        services: [],
        processes: [],
      }
    : domain === "ETL"
      ? {
          platform: "PENTAHO",
          vm_resource_id: null,
          jobchain: "",
          scheduler: "",
          log_paths: [],
          frequency_seconds: 30,
          connector_url: null,
          credential_ref: null,
          connector_records_field: "records",
        }
      : {
          dns: "",
          port: 443,
          protocol: "HTTPS",
          path: "/",
          frequency_seconds: 30,
          method: "GET",
          auth_type: "NONE",
          credential_ref: null,
          timeout_seconds: 10,
          headers: {},
          tls_validation: true,
          linked_vm_resource_id: null,
          probe_location: "NATIVE",
        }),
});
function Modal({ title, onClose, children, focus = true, workspace = false }) {
  const ref = useRef(null);
  useDialogFocus(ref, focus && !workspace, onClose);
  useEffect(() => {
    if (!workspace) return;
    const previous = document.activeElement;
    ref.current?.querySelector("h1")?.focus();
    return () => { if (previous?.isConnected) previous.focus(); };
  }, [workspace]);
  if (workspace) return (
    <section ref={ref} className="resource-onboarding-workspace" aria-label={title}>
      <div className="page-heading">
        <div><p className="muted">RESOURCE MANAGEMENT / CONFIGURATION</p><h1 tabIndex={-1}>{title}</h1></div>
        <button aria-label="Close resource form" onClick={onClose}>Close workspace</button>
      </div>
      {children}
    </section>
  );
  return (
    <div className="modal-backdrop">
      <section
        ref={ref}
        className="modal resource-onboarding-modal unified-modal"
        role="dialog"
        aria-label={title}
        aria-modal="true"
      >
        <div className="page-heading">
          <h2>{title}</h2>
          <button aria-label="Close resource form" onClick={onClose}>
            ×
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}
export default function UnifiedResourceManagement({ user, onCustomerCreated, section, onSectionChange }) {
  const [area, setArea] = useState(section || ["resources", "organizations", "delivery"].find((candidate) => canOpenSection(user, "Resource Management", candidate)) || "resources"),
    [domain, setDomain] = useState("VM"),
    [customers, setCustomers] = useState([]),
    [customer, setCustomer] = useState(""),
    [environment, setEnvironment] = useState(""),
    [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0),
    [data, setData] = useState(null),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(null),
    [form, setForm] = useState(null),
    [reload, setReload] = useState(0),
    [collector, setCollector] = useState(null),
    [source, setSource] = useState(null),
    [issues, setIssues] = useState([]),
    [link, setLink] = useState({
      depends_on_id: "",
      relationship_type: "DEPENDS_ON",
      service_identity: "",
    }),
    [parents, setParents] = useState([]),
    [legacyConfiguration, setLegacyConfiguration] = useState(false),
    [busy, setBusy] = useState(false);
  useEffect(()=>{
    // The canonical Organization and Collector lists use the explicit global
    // customer selection. The legacy resource tabs retain their own filter.
    setAdministrativeCustomers(["organizations", "collectors"].includes(area)
      ? null : customer ? [customer] : customers.map(c => c.id));
    return () => setAdministrativeCustomers(null);
  },[area,customer,customers]);
  const seq = useRef(0);
  const control = (path, method, payload, options={}) => scopedControl(path, method, payload, {...options,customerIds:customer?[customer]:customers.map(c=>c.id)});
  const allowed = (key, org) => hasPermission(user, key, org);
  const refresh = () => setReload((v) => v + 1);
  useEffect(() => {
    if (["organizations", "resources", "collectors", "parameters", "rules", "delivery"].includes(section)) {
      setArea(section);
      setSelected(null);
      setCollector(null);
      setSource(null);
    }
  }, [section]);
  const chooseArea = (next) => {
    if (!canOpenSection(user, "Resource Management", next)) return;
    setArea(next);
    setSelected(null);
    onSectionChange?.(next);
  };
  useEffect(() => {
    let live = true;
    fetchAuthorizedCustomers()
      .then((v) => live && setCustomers(v))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [reload, user.authorization_revision]);
  useEffect(() => {
    const version = ++seq.current;
    setData(null);
    setError("");
    if (!["resources", "parameters", "rules"].includes(area)) return;
    const q = new URLSearchParams({
      domain,
      limit: "50",
      offset: String(offset),
      search,
    });
    if (customer) q.append("organization_id", customer);
    if (environment) q.set("environment", environment);
    control(base + "/resources?" + q)
      .then((v) => {
        if (seq.current === version) setData(v);
      })
      .catch((e) => seq.current === version && setError(e.message));
    return () => {
      seq.current++;
    };
  }, [area, domain, customer, environment, search, offset, reload, customers]);
  useEffect(() => {
    setSelected(null);
    setLegacyConfiguration(false);
    setOffset(0);
  }, [domain, customer, environment]);
  useEffect(() => {
    let live = true;
    if (selected)
      Promise.all([
        control(base + "/resources/" + selected.id),
        control(base + "/resources?limit=200"),
      ])
        .then(([v, p]) => {
          if (live) {
            setSelected((current) => (current?.id === v.id ? v : current));
            setParents(p.items);
          }
        })
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [selected?.id, reload]);
  const inspect = (r) => {
    setSelected(r);
    setError("");
  };
  const action = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
      refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const openCollector = async (r) => {
    try {
      if (!r.primary_collector_id || !r.data_source_id)
        throw Error(
          "This VM has no complete source and Collector association. Reconcile its legacy registration before configuring collection.",
        );
      const c = await control(
        "/api/v1/monitoring/collectors/" + r.primary_collector_id,
        "GET", undefined, { customerIds: [r.organization_id] },
      );
      const s = await control(
        "/api/v1/monitoring/data-sources/" + r.data_source_id,
        "GET", undefined, { customerIds: [r.organization_id] },
      );
      setCollector(c);
      setSource(s);
    } catch (e) {
      setError(e.message);
    }
  };
  const formView = form && (
    <ResourceForm
      {...form}
      user={user}
      customers={customers}
      onClose={() => setForm(null)}
      onSaved={(r) => {
        if (!form.item) setCustomer(r.organization_id);
        refresh();
        setSelected(r);
        onCustomerCreated?.();
      }}
    />
  );
  if (form) return formView;
  return (
    <div className="resource-management-v2 unified-resources">
      {!["organizations", "collectors"].includes(area) && <div className="page-heading">
        <div>
          <h1>Resource Management</h1>
          <p>
            VM-associated collection, native ETL execution monitoring and
            endpoint probes.
          </p>
        </div>
        <div className="page-header-actions">
          <button className="filter-button" onClick={refresh}>Refresh</button>
          {area === "resources" && allowed("resources.create") && (
            <button className="primary-button" onClick={() => setForm({ domain })}>
              Create {domain === "ETL" ? "Legacy Data Pipeline" : domain === "VM" ? "Compute Instance" : "API Endpoint"}
            </button>
          )}
        </div>
      </div>}
      <label className="resource-section-select">
        <span>Resource Management component</span>
        <select value={area} onChange={(event) => chooseArea(event.target.value)}>
          {canOpenSection(user, "Resource Management", "organizations") && <option value="organizations">Organizations</option>}
          {canOpenSection(user, "Resource Management", "resources") && <option value="resources">Data Sources / Resources</option>}
          {canOpenSection(user, "Resource Management", "collectors") && <option value="collectors">Collectors</option>}
          {canOpenSection(user, "Resource Management", "parameters") && <option value="parameters">Event Parameters</option>}
          {canOpenSection(user, "Resource Management", "rules") && <option value="rules">Alert Rules</option>}
          {canOpenSection(user, "Resource Management", "delivery") && <option value="delivery">Notification Delivery</option>}
        </select>
      </label>
      {["organizations", "collectors"].includes(area) && (
        <ResourceManagementV2 user={user} section={area} embedded onOrganizationSaved={onCustomerCreated} />
      )}
      {!["organizations", "collectors"].includes(area) && <>
      <div
        role="tablist"
        aria-label={
          area === "resources"
            ? "Data Resource domains"
            : "Event Parameter domains"
        }
        className="heading-actions"
      >
        {area !== "delivery" &&
          ["VM", "ETL", "API"].map((v) => (
            <button
              key={v}
              role="tab"
              aria-selected={domain === v}
              onClick={() => setDomain(v)}
            >
              {area === "resources"
                ? domainNames[v]
                : area === "rules"
                  ? alertNames[v]
                  : parameterNames[v]}
            </button>
          ))}
      </div>
      {area === "delivery" && (
        <EventDelivery kind="delivery" organizations={customers} user={user} />
      )}
      {area === "rules" && (
        <p>
          Select a resource to configure its native alert evaluation and
          parameter version.
        </p>
      )}
      <div className="resource-toolbar" hidden={area === "delivery"}>
        <Field label="Resource customer filter">
          <select
            value={customer}
            onChange={(e) => {
              setCustomer(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All authorized customers</option>
            {customers.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </Field>
        <Field label="Resource environment filter">
          <select
            value={environment}
            onChange={(e) => {
              setEnvironment(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All environments</option>
            {["PROD", "QA", "TEST", "DEV", "SANDBOX"].map((e) => (
              <option key={e}>{e}</option>
            ))}
          </select>
        </Field>
        <Field label="Search resources">
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
          />
        </Field>
      </div>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data && !error && <p>Loading authorized resources…</p>}
      <section
        className="card table-wrap inventory-scroll"
        aria-label={(area === "resources" ? domainNames[domain] : parameterNames[domain]) + " records"}
        tabIndex={0}
      >
        <h2>
          {area === "resources" ? domainNames[domain] : parameterNames[domain]}
        </h2>
        <table>
          <thead>
            <tr>
              <th>Resource</th>
              <th>Customer</th>
              <th>Environment</th>
              <th>{domain === "ETL" ? "Platform / VM" : "Identity"}</th>
              <th>Configuration state</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.items.map((r) => (
              <tr key={r.id}>
                <td>
                  <button
                    className="resource-name-link"
                    onClick={() => inspect(r)}
                  >
                    {r.name}
                  </button>
                  <small>{r.id}</small>
                </td>
                <td>{r.inherited.customer}</td>
                <td>{r.environment}</td>
                <td>
                  {domain === "ETL"
                    ? r.configuration.platform +
                      " · " +
                      (r.inherited.hostname || "SaaS / no VM")
                    : domain === "VM"
                      ? r.configuration.hostname
                      : r.inherited.dns || r.configuration.endpoint}
                </td>
                <td>
                  {r.activation_status}
                  <small>{r.active ? "Configuration enabled · health in Operations" : "Configuration inactive"}</small>
                </td>
                <td>
                  <div className="row-actions">
                    <button onClick={() => inspect(r)}>
                      {area === "parameters"
                        ? "Configure parameters"
                        : "Details"}
                    </button>
                    {area === "resources" &&
                      allowed("resources.update", r.organization_id) &&
                      !r.configuration.legacy && (
                        <button onClick={() => setForm({ domain, item: r })}>
                          Edit
                        </button>
                      )}
                    {domain === "VM" &&
                      area === "resources" &&
                      r.primary_collector_id &&
                      allowed("collectors.view", r.organization_id) && (
                        <button onClick={() => openCollector(r)}>
                          Collector Configuration
                        </button>
                      )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !data.items.length && (
          <p>No resources match these authorized filters.</p>
        )}
      </section>
      {data && (
        <div className="form-footer">
          <span>
            {data.total} resources · page {Math.floor(offset / 50) + 1}
          </span>
          <button
            disabled={!offset}
            onClick={() => setOffset((v) => Math.max(0, v - 50))}
          >
            Previous
          </button>
          <button
            disabled={!data.has_more}
            onClick={() => setOffset((v) => v + 50)}
          >
            Next
          </button>
        </div>
      )}
      {area === "resources" && domain === "ETL" && (
        <DataPipelineIntegrations
          existingOnly
          user={user}
          customers={customers}
          organizationId={customer}
          onResourceSelected={(id) =>
            action(async () =>
              setSelected(await control(base + "/resources/" + id)),
            )
          }
        />
      )}
      {selected && (
        <section
          className="card unified-resource-detail"
          aria-label="Resource details"
        >
          <div className="page-heading">
            <h2>{selected.name}</h2>
            <button onClick={() => setSelected(null)}>Close details</button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Inherited identity</th>
                  <th>Value</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(selected.inherited).map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td>{String(v ?? "Unmapped")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {selected.data_source_id &&
            allowed("templates.view", selected.organization_id) &&
            allowed("collectors.view", selected.organization_id) && (
              <>
                <button onClick={() => setLegacyConfiguration((v) => !v)}>
                  {legacyConfiguration ? "Hide" : "Open"} legacy monitoring
                  configuration
                </button>
                {legacyConfiguration && (
                  <MonitoringSetup
                    key={selected.id}
                    embedded
                    lockedSourceId={selected.data_source_id}
                    organizationId={selected.organization_id}
                    organizationName={selected.inherited.customer}
                    user={user}
                  />
                )}
              </>
            )}
          {selected.configuration.legacy && (
            <p className="muted">
              Existing identity/history is preserved. Review legacy
              source/template mappings before activating the new engines.
            </p>
          )}
          {area === "rules" ? (
            <NativeAlertSetup resource={selected} user={user} />
          ) : area === "parameters" ? (
            <DomainParameters
              key={selected.id + selected.revision}
              resource={selected}
              user={user}
              onSaved={refresh}
            />
          ) : (
            <>
              {selected.domain === "VM" && (
                <button
                  className="primary-button"
                  disabled={!selected.primary_collector_id}
                  onClick={() => openCollector(selected)}
                >
                  Agent Installation and Collector Configuration
                </button>
              )}
              {selected.domain === "ETL" &&
                user.platform_admin &&
                selected.configuration.integration_configuration &&
                allowed("etl.configure", selected.organization_id) &&
                allowed("collectors.manage", selected.organization_id) && (
                  <PipelineConnection resource={selected} />
                )}
              <button
                onClick={() =>
                  action(async () => {
                    const v = await control(
                      base + "/resources/" + selected.id + "/verification",
                    );
                    setSelected((r) => ({ ...r, verification: v }));
                  })
                }
              >
                Verify telemetry
              </button>
              {selected.verification && (
                <Verification data={selected.verification} />
              )}
              {["API", "ETL"].includes(selected.domain) &&
                selected.primary_collector_id &&
                user.platform_admin && (
                  <button
                    onClick={() => {
                      if (
                        confirm(
                          "Approve read-only native collection for this configured deployment-approved destination?",
                        )
                      )
                        action(() =>
                          control(
                            base + "/resources/" + selected.id + "/start-probe",
                            "POST",
                            { approve: true },
                          ),
                        );
                    }}
                  >
                    Approve native probe / metadata collection
                  </button>
                )}
              <button
                onClick={() => {
                  setArea("parameters");
                }}
              >
                Open {parameterNames[selected.domain]}
              </button>
              {allowed("resources.update", selected.organization_id) && (
                <button
                  disabled={busy}
                  onClick={() => {
                    if (
                      confirm(
                        "Activate monitoring only if parameter validation and actual telemetry checks pass?",
                      )
                    )
                      action(() =>
                        control(
                          base + "/resources/" + selected.id + "/activate",
                          "POST",
                          { approve: true },
                        ),
                      );
                  }}
                >
                  Activate monitoring
                </button>
              )}
              <h3>Resource relationships</h3>
              <p className="muted">{selected.dependencies?.length || 0} of {selected.dependency_total ?? selected.dependencies?.length ?? 0} retained relationships</p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Dependency resource</th>
                      <th>Relationship</th>
                      <th>Service/process</th>
                      <th>Valid from / to</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selected.dependencies?.map((d) => (
                      <tr key={d.id}>
                        <td>
                          {parents.find((r) => r.id === d.depends_on_id)
                            ?.name || d.depends_on_id}
                        </td>
                        <td>{d.relationship_type}</td>
                        <td>{d.service_identity || "Resource"}</td>
                        <td>
                          {d.valid_from}
                          <small>{d.valid_to || "Current"}</small>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
                  {selected.dependency_has_more && (
                    <button
                      onClick={async () => {
                        const id = selected.id;
                        try {
                          const page = await control(
                            base +
                              "/resources/" +
                              id +
                              "/dependencies?limit=50&offset=" +
                              selected.dependencies.length,
                          );
                          setSelected((current) =>
                            current?.id === id
                              ? {
                                  ...current,
                                  dependencies: [
                                    ...new Map(
                                      [
                                        ...current.dependencies,
                                        ...page.items,
                                      ].map((row) => [row.id, row]),
                                    ).values(),
                                  ],
                                  dependency_total: page.total,
                                  dependency_has_more: page.has_more,
                                }
                              : current,
                          );
                        } catch (e) {
                          setError(e.message);
                        }
                      }}
                    >
                      Load more relationships
                    </button>
                  )}
              {allowed("resources.update", selected.organization_id) && (
                <div className="form-grid">
                  <Field label="Dependency resource">
                    <select
                      value={link.depends_on_id}
                      onChange={(e) =>
                        setLink((l) => ({
                          ...l,
                          depends_on_id: e.target.value,
                        }))
                      }
                    >
                      <option value="">Select authorized resource</option>
                      {parents
                        .filter(
                          (r) =>
                            r.id !== selected.id &&
                            r.organization_id === selected.organization_id &&
                            r.environment === selected.environment,
                        )
                        .map((r) => (
                          <option key={r.id} value={r.id}>
                            {r.name}
                          </option>
                        ))}
                    </select>
                  </Field>
                  <Field label="Relationship type">
                    <select
                      value={link.relationship_type}
                      onChange={(e) =>
                        setLink((l) => ({
                          ...l,
                          relationship_type: e.target.value,
                        }))
                      }
                    >
                      <option>DEPENDS_ON</option>
                      <option>REQUIRES_SERVICE</option>
                    </select>
                  </Field>
                  {link.relationship_type === "REQUIRES_SERVICE" && (
                    <Field label="Configured service/process identity">
                      <input
                        value={link.service_identity}
                        onChange={(e) =>
                          setLink((l) => ({
                            ...l,
                            service_identity: e.target.value,
                          }))
                        }
                      />
                    </Field>
                  )}
                  <button
                    disabled={!link.depends_on_id || busy}
                    onClick={() =>
                      action(() =>
                        control(
                          base + "/resources/" + selected.id + "/dependencies",
                          "POST",
                          link,
                        ),
                      )
                    }
                  >
                    Save dependency
                  </button>
                </div>
              )}
              <h3>Current conditions</h3>
              <ConditionTable rows={selected.conditions || []} />
            </>
          )}
        </section>
      )}
      {area === "resources" && domain === "VM" && (
        <details>
          <summary>Imported discovery inventory</summary>
          <ImportedDiscoveryInventory
            organizationId={customer}
            collectorOrganizations={customers
              .filter((c) => allowed("collectors.view", c.id))
              .map((c) => c.id)}
            authorizationRevision={user.authorization_revision}
          />
        </details>
      )}
      <details>
        <summary>Legacy mapping reconciliation</summary>
        <button
          onClick={() =>
            action(async () =>
              setIssues(await control(base + "/mapping-issues")),
            )
          }
        >
          Load mapping issues
        </button>
        {issues.map((i) => (
          <p key={i.id}>
            {i.entity_type} · {i.entity_id} · {i.reason}
          </p>
        ))}
        <p className="muted">
          Unmapped records are retained. No resource or history is deleted by
          this view.
        </p>
      </details>
      {formView}
      {collector && source && (
        <CollectorControl
          collector={collector}
          sources={[source]}
          user={user}
          onClose={() => {
            setCollector(null);
            setSource(null);
            refresh();
          }}
          onSaved={refresh}
        />
      )}
      </>}
    </div>
  );
}
export function ConditionTable({ rows }) {
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Condition</th>
            <th>Severity</th>
            <th>State</th>
            <th>Evidence</th>
            <th>Last observed</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr key={c.id}>
              <td>{c.message}</td>
              <td>{c.severity}</td>
              <td>{c.active ? "OPEN" : "RESOLVED"}</td>
              <td>
                <details>
                  <summary>Supporting evidence</summary>
                  <pre>{JSON.stringify(c.evidence, null, 2)}</pre>
                </details>
              </td>
              <td>{c.last_observed_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!rows.length && <p>No evaluated conditions.</p>}
    </div>
  );
}
export function Verification({ data }) {
  return (
    <section aria-label="Telemetry verification">
      <h3>
        Telemetry verification · {data.ready ? "Verified" : "Not verified"}
      </h3>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Required check</th>
              <th>Observed result</th>
            </tr>
          </thead>
          <tbody>
            {data.checks.map((c) => (
              <tr key={c.name}>
                <td>{c.name}</td>
                <td>
                  {c.passed ? "PASS" : "NOT VERIFIED"}
                  {c.last_received_at && <small>{c.last_received_at}</small>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
function ResourceForm({ domain, item, user, customers, onClose, onSaved }) {
  const [form, setForm] = useState(
      item
        ? {
            ...blank(domain),
            ...item.configuration,
            name: item.name,
            organization_id: item.organization_id,
            environment: item.environment,
            active: item.active,
          }
        : blank(domain),
    ),
    [vms, setVMs] = useState([]),
    [inline, setInline] = useState(false),
    [customerName, setCustomerName] = useState(""),
    [customerCode, setCustomerCode] = useState(""),
    [step, setStep] = useState(1),
    [maxUnlockedStep, setMaxUnlockedStep] = useState(1),
    [draftId, setDraftId] = useState(null),
    [draftRevision, setDraftRevision] = useState(null),
    [drafts, setDrafts] = useState([]),
    [created, setCreated] = useState(item || null),
    [source, setSource] = useState(null),
    [collector, setCollector] = useState(null),
    [openCollector, setOpenCollector] = useState(false),
    [verification, setVerification] = useState(null),
    [approved, setApproved] = useState(false),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [imported, setImported] = useState(null),
    [fileName, setFileName] = useState("");
  useEffect(() => {
    let live = true;
    if (domain !== "VM")
      control(base + "/resources?domain=VM&limit=200")
        .then((v) => live && setVMs(v.items))
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [domain]);
  useEffect(() => {
    let live = true;
    if (created?.primary_collector_id && !created.data_source_id && domain === "VM")
      setError("This VM has no canonical Data Source association. Reconcile the legacy registration before configuring collection.");
    if (created?.primary_collector_id && created.data_source_id && domain === "VM")
      Promise.all([
        control("/api/v1/monitoring/data-sources/" + created.data_source_id, "GET", undefined, { customerIds: [created.organization_id] }),
        control(
          "/api/v1/monitoring/collectors/" + created.primary_collector_id,
          "GET", undefined, { customerIds: [created.organization_id] },
        ),
      ])
        .then(([s, c]) => {
          if (live) {
            setSource(s);
            setCollector(c);
          }
        })
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [created?.id, domain]);
  useEffect(() => {
    let live = true;
    if (!item)
      control("/api/v1/resource-drafts?domain=" + domain)
        .then((v) => live && setDrafts(v.items || v))
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [domain, item]);
  const saveDraft = () =>
    action(async () => {
      const configuration = { ...form, resource_id: created?.id || null };
      const payload = {
        domain,
        name: form.name || "Untitled " + domain,
        organization_id: form.organization_id || null,
        stage: step,
        configuration,
      };
      if (draftRevision != null) payload.expected_revision = draftRevision;
      const v = await control(
        "/api/v1/resource-drafts" + (draftId ? "/" + draftId : ""),
        draftId ? "PUT" : "POST",
        payload,
      );
      setDraftId(v.id);
      setDraftRevision(v.revision);
    });
  const resumeDraft = async (id) =>
    action(async () => {
      const v = await control("/api/v1/resource-drafts/" + id);
      const { resource_id, ...configuration } = v.configuration;
      setForm({ ...blank(domain), ...configuration });
      setStep(v.stage);
      setMaxUnlockedStep(v.stage);
      setDraftId(v.id);
      setDraftRevision(v.revision);
      if (resource_id)
        setCreated(await control(base + "/resources/" + resource_id));
    });
  const update = (k, v) => {
    setForm((f) => ({ ...f, [k]: v }));
    setVerification(null);
    setApproved(false);
  };
  const inherited =
    domain === "ETL" ? vms.find((r) => r.id === form.vm_resource_id) : null;
  const action = async (fn) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const save = () =>
    action(async () => {
      if (!form.name.trim()) throw Error("Resource name required");
      if (!item && !inline && !form.organization_id)
        throw Error("Select a monitored customer organization before saving the resource");
      if (inline && (!customerName.trim() || !customerCode.trim()))
        throw Error("Enter the new customer name and code before saving");
      if (domain === "VM" && (!form.hostname.trim() || !form.address.trim()))
        throw Error("Hostname and DNS/IP address are required before saving a Compute Instance");
      if (domain === "ETL" && !form.jobchain.trim())
        throw Error("Jobchain name is required before saving a Data Pipeline");
      if (domain === "API" && !form.dns.trim())
        throw Error("Endpoint DNS name is required before saving an API Endpoint");
      let payload = {
        ...form,
        new_customer: inline
          ? { name: customerName, code: customerCode }
          : null,
        organization_id: inline ? null : form.organization_id || null,
      };
      if (inherited) {
        payload.organization_id = inherited.organization_id;
        payload.environment = inherited.environment;
        payload.new_customer = null;
      }
      delete payload.legacy;
      delete payload.legacy_template_attachments;
      let r = created;
      if (item || created) {
        const existing = item || created;
        const config = { ...form };
        for (const key of [
          "name",
          "organization_id",
          "new_customer",
          "environment",
          "active",
        ])
          delete config[key];
        r = await control(base + "/resources/" + existing.id, "PUT", {
          expected_revision: existing.revision,
          name: form.name,
          environment: form.environment,
          configuration: config,
          active: form.active,
        });
      } else if (!r)
        r = await control(
          base + "/resources/" + domain.toLowerCase(),
          "POST",
          payload,
        );
      setCreated(r);
      await onSaved(r);
      if (imported) {
        await control(base + "/parameters/" + r.id, "POST", {
          expected_resource_revision: r.revision,
          configuration: imported.configuration,
        }, { customerIds: [r.organization_id] });
        setImported(null);
      }
      if (domain === "VM" && !item) {
        setStep(2);
        setMaxUnlockedStep((current) => Math.max(current, 2));
      }
      else onClose();
    });
  const chooseVM = (id) => {
    const vm = vms.find((r) => r.id === id);
    update(
      domain === "ETL" ? "vm_resource_id" : "linked_vm_resource_id",
      id || null,
    );
    if (vm) {
      update("organization_id", vm.organization_id);
      update("environment", vm.environment);
      setInline(false);
    }
  };
  const visibleStep = domain === "VM" && !created ? 1 : step;
  const guidedSteps = domain === "VM"
    ? [
        "Create Compute Instance",
        "Configure Telemetry",
        "Install Agent",
        "Verify Connection",
        "Configure Collection",
        "Configure Event Parameters",
        "Configure Alert Rules",
        "Configure Notification Delivery",
        "Validate Configuration",
        "Activate Monitoring",
      ]
    : ["Resource identity", domain === "ETL" ? "Pipeline configuration" : "Probe configuration", "Review and save"];
  const identityReady = Boolean(
    form.name.trim() && form.environment &&
    (form.organization_id || (inline && customerName.trim() && customerCode.trim())),
  );
  return (
    <Modal
      title={
        (item ? "Edit " : "Create ") +
        (domain === "ETL"
          ? "Data Pipeline"
          : domain === "VM"
            ? "Compute Instance"
            : "API Endpoint")
      }
      onClose={onClose}
      focus={!openCollector}
      workspace
    >
        <ol className="onboarding-steps" aria-label={`${domain === "VM" ? "VM" : domain === "ETL" ? "Data Pipeline" : "API Endpoint"} onboarding steps`}>
          {guidedSteps.map((s, i) => (
            <li key={s} className={visibleStep === i + 1 ? "onboarding-step active" : "onboarding-step"}>
              <button
                type="button"
                aria-current={visibleStep === i + 1 ? "step" : undefined}
                disabled={i + 1 > maxUnlockedStep || (domain === "VM" && !created && i > 0)}
                onClick={() => setStep(i + 1)}
              >
                {i + 1}. {s}
              </button>
            </li>
          ))}
        </ol>
      <div className="resource-onboarding-content">
      {error && <p className="error-banner" role="alert">{error}</p>}
      {!item && <div className="heading-actions">
        <button disabled={busy} onClick={saveDraft}>Save draft</button>
        {drafts.length > 0 && <label>Resume draft
          <select defaultValue="" onChange={(e) => e.target.value && resumeDraft(e.target.value)}>
            <option value="">Select saved draft</option>
            {drafts.map((d) => <option key={d.id} value={d.id}>{d.name} · stage {d.stage}</option>)}
          </select>
        </label>}
      </div>}
      {visibleStep === 1 && (
        <>
          <DynamicConfigurationForm
            definition={domain}
            value={form}
            onChange={(next) => { setForm(next); setVerification(null); setApproved(false); }}
            keys={["environment"]}
            disabled={!!inherited}
          />
          <div className="form-grid">
            <Field label="Resource name">
              <input
                required
                value={form.name}
                onChange={(e) => update("name", e.target.value)}
              />
            </Field>
            {domain === "ETL" && (
              <Field label="ETL platform">
                <select
                  value={form.platform}
                  onChange={(e) => update("platform", e.target.value)}
                >
                  <option>PENTAHO</option>
                  <option>IICS</option>
                  {[
                    "AIRFLOW",
                    "NIFI",
                    "ADF",
                    "AWS_GLUE",
                    "SSIS",
                    "TALEND",
                    "CUSTOM",
                  ].map((p) => (
                    <option key={p}>{p}</option>
                  ))}
                </select>
              </Field>
            )}
            {domain !== "VM" && (
              <Field
                label={
                  domain === "ETL" ? "Associated VM" : "Linked VM (optional)"
                }
              >
                <select
                  value={
                    form.vm_resource_id || form.linked_vm_resource_id || ""
                  }
                  onChange={(e) => chooseVM(e.target.value)}
                >
                  <option value="">No VM / SaaS</option>
                  {vms.map((r) => (
                    <option key={r.id} value={r.id}>
                      {r.name} · {r.environment}
                    </option>
                  ))}
                </select>
              </Field>
            )}
            <Field label="Customer">
              <select
                disabled={!!inherited || inline || !!item}
                value={form.organization_id || ""}
                onChange={(e) => update("organization_id", e.target.value)}
              >
                <option value="">Select existing customer</option>
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
              {inherited && <small>INHERITED from selected VM</small>}
            </Field>
          </div>
          {!inherited && !item && hasPermission(user, "customers.create") && (
            <label>
              <input
                type="checkbox"
                checked={inline}
                disabled={!user.platform_admin}
                onChange={(e) => setInline(e.target.checked)}
              />{" "}
              Create customer inline{" "}
              {!user.platform_admin && (
                <small>
                  Platform administration is required for a new customer scope.
                </small>
              )}
            </label>
          )}
          {inline && (
            <div className="form-grid">
              <Field label="New customer name">
                <input
                  required
                  value={customerName}
                  onChange={(e) => setCustomerName(e.target.value)}
                />
              </Field>
              <Field label="New customer code">
                <input
                  required
                  value={customerCode}
                  onChange={(e) => setCustomerCode(e.target.value)}
                />
              </Field>
            </div>
          )}
          {domain === "VM" && (
            <>
              <div className="form-grid">
                <Field label="Hostname">
                  <input
                    required
                    value={form.hostname}
                    disabled={!!item}
                    onChange={(e) => update("hostname", e.target.value)}
                  />
                </Field>
                <Field label="DNS / IP address">
                  <input
                    required
                    value={form.address}
                    onChange={(e) => update("address", e.target.value)}
                  />
                </Field>
                <Field label="OS">
                  <select
                    value={form.os_type}
                    disabled={!!item}
                    onChange={(e) => update("os_type", e.target.value)}
                  >
                    <option>Linux</option>
                    <option>Windows</option>
                  </select>
                </Field>
                <Field label="Deployment Type">
                  <select
                    value={form.deployment_type}
                    onChange={(e) => {
                      update("deployment_type", e.target.value);
                      update(
                        "vm_type",
                        e.target.value === "PUBLIC_INSTANCES" ? "EC2" : "VM",
                      );
                    }}
                  >
                    <option value="PRIVATE_CLOUD">Private Cloud</option>
                    <option value="PUBLIC_INSTANCES">Public Instances</option>
                  </select>
                </Field>
              </div>
              <label>
                <input
                  type="checkbox"
                  checked={form.native_os_metrics}
                  onChange={(e) =>
                    update("native_os_metrics", e.target.checked)
                  }
                />{" "}
                Collect native host metrics
              </label>
              <Field label="Service names (one per line)">
                <textarea
                  value={form.services.join("\n")}
                  onChange={(e) =>
                    update(
                      "services",
                      e.target.value.split("\n").filter(Boolean),
                    )
                  }
                />
              </Field>
              <Field label="Process names (one per line)">
                <textarea
                  value={form.processes.join("\n")}
                  onChange={(e) =>
                    update(
                      "processes",
                      e.target.value.split("\n").filter(Boolean),
                    )
                  }
                />
              </Field>
            </>
          )}
        </>
      )}
      {domain !== "VM" && visibleStep === 2 && (
        <>
          {domain === "ETL" && (
            <>
              <div className="form-grid">
                <Field label="Jobchain name">
                  <input
                    value={form.jobchain}
                    disabled={!!item}
                    onChange={(e) => update("jobchain", e.target.value)}
                  />
                </Field>
                <Field label="Scheduler details">
                  <input
                    value={form.scheduler || ""}
                    onChange={(e) => update("scheduler", e.target.value)}
                  />
                </Field>
                <Field label="Collection frequency (seconds)">
                  <input
                    type="number"
                    min="5"
                    value={form.frequency_seconds}
                    onChange={(e) =>
                      update("frequency_seconds", Number(e.target.value))
                    }
                  />
                </Field>
              </div>
              {inherited && (
                <p>
                  INHERITED · {inherited.inherited.hostname} · Collector{" "}
                  {inherited.primary_collector_id || "Requires reconciliation"}
                </p>
              )}
              {form.platform === "PENTAHO" && (
                <Field label="Log file paths (one per line)">
                  <textarea
                    value={form.log_paths.join("\n")}
                    onChange={(e) =>
                      update(
                        "log_paths",
                        e.target.value.split("\n").filter(Boolean),
                      )
                    }
                  />
                </Field>
              )}
              <DynamicConfigurationForm
                definition={"PLATFORM_" + form.platform}
                value={form.integration_configuration || {}}
                onChange={(v) => update("integration_configuration", v)}
              />
              {form.platform === "IICS" && (
                <div className="form-grid">
                  <Field label="Read-only execution metadata URL">
                    <input
                      value={form.connector_url || ""}
                      placeholder="https://approved-region.example/activity"
                      onChange={(e) =>
                        update("connector_url", e.target.value || null)
                      }
                    />
                  </Field>
                  <Field label="Cloud token secret reference">
                    <input
                      value={form.credential_ref || ""}
                      placeholder="env:IICS_ACCESS_TOKEN"
                      onChange={(e) =>
                        update("credential_ref", e.target.value || null)
                      }
                    />
                  </Field>
                  <Field label="Execution inventory field">
                    <input
                      value={form.connector_records_field}
                      onChange={(e) =>
                        update("connector_records_field", e.target.value)
                      }
                    />
                  </Field>
                </div>
              )}
              <Field label="ETL YAML/JSON configuration">
                <input
                  type="file"
                  accept=".yaml,.yml,.json"
                  onChange={(e) =>
                    action(async () => {
                      const file = e.target.files[0];
                      if (!file) return;
                      if (file.size > 262144)
                        throw Error("Import exceeds 256 KiB");
                      const v = await control(
                        base + "/import/validate",
                        "POST",
                        {
                          domain: "ETL",
                          format: file.name.endsWith(".json") ? "JSON" : "YAML",
                          content: await file.text(),
                        },
                      );
                      setImported(v);
                      setFileName(file.name);
                      update("parser", v.configuration.parser);
                      update("schedule", v.configuration.schedule);
                    })
                  }
                />
              </Field>
              {imported && (
                <>
                  <p>{fileName} · validated, not activated</p>
                  <pre>{JSON.stringify(imported.configuration, null, 2)}</pre>
                </>
              )}
            </>
          )}
          {domain === "API" && (
            <div className="form-grid">
              <Field label="DNS / hostname">
                <input
                  value={form.dns}
                  disabled={!!item}
                  onChange={(e) => update("dns", e.target.value)}
                />
              </Field>
              <Field label="Port">
                <input
                  type="number"
                  min="1"
                  max="65535"
                  value={form.port}
                  disabled={!!item}
                  onChange={(e) => update("port", Number(e.target.value))}
                />
              </Field>
              <Field label="Protocol">
                <select
                  value={form.protocol}
                  disabled={!!item}
                  onChange={(e) => update("protocol", e.target.value)}
                >
                  <option>HTTPS</option>
                  <option>HTTP</option>
                </select>
              </Field>
              <Field label="URL path">
                <input
                  value={form.path}
                  disabled={!!item}
                  onChange={(e) => update("path", e.target.value)}
                />
              </Field>
              <Field label="Check frequency (seconds)">
                <input
                  type="number"
                  min="5"
                  value={form.frequency_seconds}
                  onChange={(e) =>
                    update("frequency_seconds", Number(e.target.value))
                  }
                />
              </Field>
              <Field label="Request method">
                <select
                  value={form.method}
                  onChange={(e) => update("method", e.target.value)}
                >
                  <option>GET</option>
                  <option>HEAD</option>
                  <option>OPTIONS</option>
                </select>
              </Field>
              <Field label="Authentication">
                <select
                  value={form.auth_type}
                  onChange={(e) => update("auth_type", e.target.value)}
                >
                  <option>NONE</option>
                  <option>BASIC</option>
                  <option>BEARER</option>
                </select>
              </Field>
              {form.auth_type !== "NONE" && (
                <Field label="Authentication secret reference">
                  <input
                    value={form.credential_ref || ""}
                    onChange={(e) =>
                      update("credential_ref", e.target.value || null)
                    }
                  />
                </Field>
              )}
              <Field label="Timeout (seconds)">
                <input
                  type="number"
                  min="1"
                  max="120"
                  value={form.timeout_seconds}
                  onChange={(e) =>
                    update("timeout_seconds", Number(e.target.value))
                  }
                />
              </Field>
              <p>
                TLS is verified. Outbound hosts, ports and CIDRs require
                deployment approval.
              </p>
            </div>
          )}
        </>
      )}
      {(domain === "VM" ? visibleStep === 1 : visibleStep === 3) && (
        <>
          {domain !== "VM" && (
            <div className="card" role="status">
              <strong>Review {domain === "ETL" ? "pipeline" : "endpoint"} identity</strong>
              <p>{form.name || "Unnamed resource"} · {form.environment || "Environment unselected"} · {customers.find((customer) => customer.id === form.organization_id)?.name || (inline ? customerName : "Customer unselected")}</p>
              <p>Saving configuration does not verify native collection or activate monitoring.</p>
            </div>
          )}
          <label>
            <input
              type="checkbox"
              checked={form.active}
              onChange={(e) => update("active", e.target.checked)}
            />
            Enable resource
          </label>
          <Field label="Description">
            <textarea
              value={form.description || ""}
              onChange={(e) => update("description", e.target.value)}
            />
          </Field>
          <div className="form-footer">
            <button onClick={onClose}>Cancel</button>
            <button className="primary-button" disabled={busy} onClick={save}>
              {busy
                ? "Saving…"
                : item
                  ? "Save resource"
                  : domain === "VM" ? "Save resource identity" : "Save configuration"}
            </button>
          </div>
        </>
      )}
      {domain === "VM" && visibleStep === 2 && (
        <>
          <h3>Collector Configuration</h3>
          <p>
            One VM-associated OpsControl Agent; independently configured
            telemetry methods.
          </p>
          <button disabled={!collector} onClick={() => setOpenCollector(true)}>
            Configure Collection Methods
          </button>
        </>
      )}
      {domain === "VM" && visibleStep === 3 && (
        <>
          <h3>Agent Installation</h3>
          <p>
            Install the OpsControl Agent locally as a Windows service or Linux
            systemd service. The Agent supervises pinned OTel Collector Contrib.
            A host address alone does not authorize remote installation.
          </p>
          <button disabled={!collector} onClick={() => setOpenCollector(true)}>
            Agent Registration and installation instructions
          </button>
          <button
            onClick={() =>
              action(() =>
                downloadPackage(
                  form.os_type === "Windows" ? "windows" : "linux",
                ),
              )
            }
          >
            Download approved agent package
          </button>
        </>
      )}
      {domain === "VM" && visibleStep === 4 && (
        <>
          <h3>Verification</h3>
          <button
            disabled={busy}
            onClick={() =>
              action(async () =>
                setVerification(
                  await control(
                    base + "/resources/" + created.id + "/verification",
                  ),
                ),
              )
            }
          >
            Verify telemetry
          </button>
          {verification && <Verification data={verification} />}
        </>
      )}
      {domain === "VM" && visibleStep === 5 && (
        <>
          <h3>Configure Collection</h3>
          <button disabled={!collector} onClick={() => setOpenCollector(true)}>
            Configure independent collection methods
          </button>
        </>
      )}
      {domain === "VM" && visibleStep === 6 && (
        <>
          <h3>Event Parameters (optional)</h3>
          <DomainParameters resource={created} user={user} />
        </>
      )}
      {domain === "VM" && visibleStep === 7 && (
        <>
          <h3>Alert Rules (optional)</h3>
          <NativeAlertSetup resource={created} user={user} />
        </>
      )}
      {domain === "VM" && visibleStep === 8 && (
        <>
          <h3>Notification Delivery (optional)</h3>
          <EventDelivery
            kind="delivery"
            organizations={customers.filter(
              (c) => c.id === created.organization_id,
            )}
            user={user}
          />
        </>
      )}
      {domain === "VM" && visibleStep === 9 && (
        <>
          <h3>Validate Configuration</h3>
          <button
            disabled={busy}
            onClick={() =>
              action(async () =>
                setVerification(
                  await control(
                    base + "/resources/" + created.id + "/verification",
                  ),
                ),
              )
            }
          >
            Validate actual readiness
          </button>
          {verification && <Verification data={verification} />}
        </>
      )}
      {domain === "VM" && visibleStep === 10 && (
        <>
          <h3>Activation</h3>
          <p>
            Event Parameters, Alert Rules and Notification Delivery are
            optional. Installation and required collection evidence remain
            mandatory.
          </p>
          {!verification?.ready && <p role="status">Run readiness validation on step 9. Activation remains unavailable until the backend confirms current telemetry evidence.</p>}
          <label>
            <input
              type="checkbox"
              checked={approved}
              onChange={(e) => setApproved(e.target.checked)}
            />{" "}
            Approve verified monitoring activation
          </label>
          <button
            className="primary-button"
            disabled={!approved || !verification?.ready || verification?.resource_id !== created?.id || busy}
            onClick={() =>
              action(async () => {
                const r = await control(
                  base + "/resources/" + created.id + "/activate",
                  "POST",
                  { approve: true },
                );
                await onSaved(r);
                onClose();
              })
            }
          >
            Activate monitoring
          </button>
        </>
      )}
      {domain === "VM" && visibleStep > 1 && <div className="onboarding-actions">
        <button onClick={() => setStep((s) => Math.max(1, s - 1))}>Previous</button>
        {visibleStep < 10 && <button className="primary-button" onClick={() => {
          const next = Math.min(10, visibleStep + 1);
          setMaxUnlockedStep((current) => Math.max(current, next));
          setStep(next);
        }}>Continue</button>}
      </div>}
      {domain !== "VM" && <div className="onboarding-actions">
        {visibleStep > 1 && <button type="button" onClick={() => setStep((current) => current - 1)}>Previous</button>}
        {visibleStep < 3 && <button type="button" className="primary-button" disabled={busy || (visibleStep === 1 && !identityReady)} onClick={() => {
          const next = visibleStep + 1;
          setMaxUnlockedStep((current) => Math.max(current, next));
          setStep(next);
        }}>Continue</button>}
      </div>}
      {openCollector && collector && source && (
        <CollectorControl
          collector={collector}
          sources={[source]}
          user={user}
          onClose={() => setOpenCollector(false)}
          onSaved={async () => {
            setVerification(null);
            setApproved(false);
            setCollector(await control("/api/v1/monitoring/collectors/" + collector.id));
          }}
        />
      )}
      </div>
    </Modal>
  );
}

function NativeAlertSetup({ resource, user }) {
  const [config, setConfig] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const editorRef = useRef(null);
  useEffect(() => {
    let live = true;
    control(base + "/resources/" + resource.id + "/alert-setup")
      .then((v) => live && setConfig(v))
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [resource.id]);
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      if (editorRef.current?.querySelector('[aria-invalid="true"]'))
        throw new Error("Correct invalid alert configuration before saving");
      setConfig(
        await control(
          base + "/resources/" + resource.id + "/alert-setup",
          "POST",
          {
            enabled: config.enabled,
            parameter_version: config.parameter_version
              ? Number(config.parameter_version)
              : null,
            severities: config.severities || ["WARNING", "CRITICAL"],
          },
        ),
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section ref={editorRef} className="card">
      <h3>Native alert setup · {resource.name}</h3>
      {error && <p role="alert">{error}</p>}
      {!config && !error && <p>Loading alert configuration…</p>}
      {config && (
        <>
          <DynamicConfigurationForm
            definition="ALERT_SETUP"
            value={config}
            keys={["enabled", "parameter_version", "severities"]}
            disabled={
              !hasPermission(user, "templates.manage", resource.organization_id)
            }
            onChange={setConfig}
          />
          <p>
            Saving parameters alone does not enable alerts. Rules evaluate the
            referenced validated parameter version.
          </p>
          {hasPermission(
            user,
            "templates.manage",
            resource.organization_id,
          ) && (
            <button disabled={busy} onClick={save}>
              Save alert setup
            </button>
          )}
        </>
      )}
    </section>
  );
}

function PipelineConnection({ resource }) {
  const [result, setResult] = useState(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const generation = useRef(0);
  useEffect(() => {
    generation.current += 1;
    setResult(null);
    setError("");
    setBusy(false);
    return () => {
      generation.current += 1;
    };
  }, [resource.id, resource.revision]);
  const test = async () => {
    const current = ++generation.current;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const observed = await control(
        base + "/resources/" + resource.id + "/test-connection",
        "POST",
      );
      if (current === generation.current) setResult(observed);
    } catch (e) {
      if (current === generation.current) setError(e.message);
    } finally {
      if (current === generation.current) setBusy(false);
    }
  };
  return (
    <section aria-label="Data Pipeline connection test">
      <button disabled={busy} onClick={test}>
        {busy ? "Testing Connection…" : "Test Connection"}
      </button>
      {error && <p role="alert">{error}</p>}
      {result && (
        <p role="status">
          {result.connected
            ? `Provider read succeeded at ${result.observed_at}. ${result.observation?.record_count ?? 0} execution records observed. This does not activate monitoring.`
            : `Connection failed: ${result.error_kind}. Monitoring is not verified.`}
        </p>
      )}
    </section>
  );
}
