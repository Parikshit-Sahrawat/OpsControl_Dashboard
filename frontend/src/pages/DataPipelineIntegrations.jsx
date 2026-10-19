import { useEffect, useRef, useState } from "react";
import { control, control as scopedControl } from "../controlPlane";
import { hasPermission } from "../permissions";
import DynamicConfigurationForm from "../components/DynamicConfigurationForm";
import { Field } from "./DomainParameters";

export const PIPELINE_STEPS = [
  "General",
  "Platform",
  "Connection",
  "Integration",
  "Collection Sources",
  "Job Discovery/Selection",
  "Source Associations",
  "Validate & Activate",
];
const api = "/api/v1/data-pipelines";
const key = () => globalThis.crypto.randomUUID();
const initial = {
  name: "",
  organization_id: "",
  environment: "DEV",
  platform: "PENTAHO",
  vm_resource_id: "",
  configuration: {},
};

export default function DataPipelineIntegrations({
  user,
  customers,
  organizationId,
  onResourceSelected,
}) {
  const [list, setList] = useState(null),
    [catalogue, setCatalogue] = useState(null),
    [editing, setEditing] = useState(null),
    [draft, setDraft] = useState(initial),
    [step, setStep] = useState(1),
    [error, setError] = useState(""),
    [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false),
    [vms, setVms] = useState([]),
    [search, setSearch] = useState(""),
    [offset, setOffset] = useState(0),
    [jobSearch, setJobSearch] = useState(""),
    [jobOffset, setJobOffset] = useState(0),
    [jobPage, setJobPage] = useState(null),
    [connection, setConnection] = useState({}),
    [profile, setProfile] = useState({
      platform_version: "unknown",
      edition: "Operator supplied",
      deployment_type: "Self-hosted",
      supported_methods: ["PLATFORM_API"],
      authentication_requirements: [],
      required_permissions: [],
    }),
    [method, setMethod] = useState({
      name: "",
      method_type: "PLATFORM_API",
      transport: "BACKEND",
      identity: { endpoint: "", account: "", physical_scope: "" },
      configuration: {},
      enabled: true,
    }),
    [job, setJob] = useState({ native_id: "", name: "" }),
    [association, setAssociation] = useState({ job_id: "", method_id: "" }),
    [reload, setReload] = useState(0);
  const sequence = useRef(0),
    detailSequence = useRef(0),
    wizardRef = useRef(null);
  const control = (path, method, payload, options = {}) =>
    scopedControl(path, method, payload, {
      ...options,
      customerIds: organizationId
        ? [organizationId]
        : editing?.organization_id
          ? [editing.organization_id]
          : draft.organization_id
            ? [draft.organization_id]
            : customers.map((c) => c.id),
    });
  const allowed = hasPermission(
    user,
    "etl.configure",
    editing?.organization_id || draft.organization_id || organizationId,
  );
  useEffect(() => {
    let live = true;
    Promise.all([
      control(api + "/catalogue"),
      control("/api/v1/unified/resources?domain=VM&limit=200"),
    ])
      .then(([c, v]) => {
        if (live) {
          setCatalogue(c);
          setVms(v.items);
        }
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [user.authorization_revision, customers]);
  useEffect(() => {
    const current = ++sequence.current;
    const q = new URLSearchParams({
      search,
      offset: String(offset),
      limit: "25",
    });
    if (organizationId) q.set("organization_id", organizationId);
    setList(null);
    control(api + "/integrations?" + q)
      .then((v) => current === sequence.current && setList(v))
      .catch((e) => current === sequence.current && setError(e.message));
    return () => {
      sequence.current++;
    };
  }, [
    organizationId,
    search,
    offset,
    reload,
    user.authorization_revision,
    customers,
  ]);
  useEffect(() => {
    detailSequence.current++;
    setEditing(null);
    setError("");
  }, [organizationId, user.authorization_revision]);
  useEffect(() => {
    setJobOffset(0);
    setJobSearch("");
    setJobPage(null);
  }, [editing?.id, step]);
  useEffect(() => {
    let live = true;
    setJobPage(null);
    if (editing?.id && (step === 6 || step === 7)) {
      const query = new URLSearchParams({
        search: jobSearch,
        offset: String(jobOffset),
        limit: "50",
      });
      if (step === 7) query.set("selected", "true");
      control(api + "/integrations/" + editing.id + "/jobs?" + query)
        .then((data) => live && setJobPage(data))
        .catch((e) => live && setError(e.message));
    }
    return () => {
      live = false;
    };
  }, [
    editing?.id,
    step,
    jobSearch,
    jobOffset,
    reload,
    user.authorization_revision,
  ]);
  async function load(id) {
    const generation = ++detailSequence.current;
    const data = await control(api + "/integrations/" + id);
    if (generation !== detailSequence.current) return null;
    setEditing(data);
    return data;
  }
  async function action(fn) {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const result = await fn();
      setReload((v) => v + 1);
      if (editing?.id) await load(editing.id);
      setNotice(
        "Saved. Configuration saving does not certify deployment or data reception.",
      );
      return result;
    } catch (e) {
      setError(e.message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  async function open(row) {
    await action(async () => {
      const data = await load(row.id);
      if (!data) return null;
      setDraft({
        name: data.name,
        organization_id: data.organization_id,
        environment: data.environment,
        platform: data.platform,
        vm_resource_id: data.vm_resource_id || "",
        configuration: data.configuration,
      });
      setStep(data.stage);
      const saved = data.configuration.wizard_inputs || {};
      setConnection(
        saved.connection || data.connections.at(-1)?.configuration || {},
      );
      if (saved.profile) setProfile(saved.profile);
      if (saved.method) setMethod(saved.method);
      if (saved.job) setJob(saved.job);
      if (saved.association) setAssociation(saved.association);
      return data;
    });
  }
  function create() {
    setEditing({
      id: null,
      methods: [],
      jobs: [],
      connections: [],
      capabilities: [],
      sources: [],
      associations: [],
      operations: [],
      activation_blockers: [],
    });
    setDraft({
      ...initial,
      organization_id:
        organizationId ||
        customers.find(
          (c) =>
            hasPermission(user, "etl.configure", c.id) &&
            hasPermission(user, "resources.create", c.id),
        )?.id ||
        "",
    });
    setStep(1);
    setError("");
    setNotice("");
  }
  async function save() {
    if (wizardRef.current?.querySelector('[aria-invalid="true"]')) {
      setError("Correct invalid JSON before saving the draft.");
      return null;
    }
    const id = editing?.id;
    const payload = {
      ...draft,
      vm_resource_id: draft.vm_resource_id || null,
      stage: step,
      configuration: {
        ...draft.configuration,
        wizard_inputs: { connection, profile, method, job, association },
      },
      idempotency_key: key(),
      ...(id ? { expected_revision: editing.revision } : {}),
    };
    const result = await action(() =>
      control(
        api + "/integrations" + (id ? "/" + id : ""),
        id ? "PUT" : "POST",
        payload,
      ),
    );
    if (result) await load(result.id);
    return result;
  }
  const selectedPlatform = catalogue?.platforms.find(
    (p) => p.platform === draft.platform,
  );
  const activeConnection =
    editing?.connections.find((c) => c.active) || editing?.connections.at(-1);
  const activeProfile = editing?.capabilities.at(-1);
  const parent = vms.find((v) => v.id === draft.vm_resource_id);
  function parentChange(id) {
    const p = vms.find((v) => v.id === id);
    setDraft((v) => ({
      ...v,
      vm_resource_id: id,
      ...(p
        ? { organization_id: p.organization_id, environment: p.environment }
        : {}),
    }));
  }
  async function addMethod() {
    if (!activeConnection || !activeProfile)
      throw new Error("Save a connection and capability profile first.");
    const identity =
      method.method_type === "FILE_LOG"
        ? {
            host_resource_id: draft.vm_resource_id,
            path: method.identity.path || "",
            os: parent?.configuration?.os_type || "Linux",
          }
        : {
            platform: draft.platform,
            endpoint: method.identity.endpoint,
            account: method.identity.account,
            physical_scope: method.identity.physical_scope,
          };
    return control(api + "/integrations/" + editing.id + "/methods", "POST", {
      ...method,
      identity,
      configuration: method.configuration,
      connection_id: activeConnection.id,
      capability_id: activeProfile.id,
      idempotency_key: key(),
    });
  }
  function post(path, payload = {}) {
    return control(api + path, "POST", { idempotency_key: key(), ...payload });
  }
  const blockers = editing?.activation_blockers || [];
  return (
    <section
      className="card pipeline-integrations"
      aria-label="Data Pipelines integrations"
    >
      <div className="page-heading">
        <div>
          <h2>Data Pipelines integrations</h2>
          <p className="muted">
            One customer-scoped platform connection, multiple jobs and
            independently owned sources.
          </p>
        </div>
        {hasPermission(user, "resources.create", organizationId) &&
          hasPermission(user, "etl.configure", organizationId) && (
            <button className="primary-button" onClick={create}>
              Create Data Pipeline
            </button>
          )}
      </div>
      <Field label="Search integrations">
        <input
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setOffset(0);
          }}
        />
      </Field>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {notice && <p role="status">{notice}</p>}
      {!list ? (
        <p role="status">Loading authorized integrations…</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col">Integration</th>
                <th scope="col">Platform</th>
                <th scope="col">Environment</th>
                <th scope="col">Collection</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {list.items.map((row) => (
                <tr key={row.id}>
                  <td>
                    <button className="link-button" onClick={() => open(row)}>
                      {row.name}
                    </button>
                  </td>
                  <td>{row.platform}</td>
                  <td>{row.environment}</td>
                  <td>
                    {row.enabled
                      ? "Enabled · evidence required"
                      : "Draft / suspended"}
                  </td>
                  <td>
                    <button onClick={() => open(row)}>View / Edit</button>
                    {hasPermission(
                      user,
                      "etl.configure",
                      row.organization_id,
                    ) &&
                      row.enabled && (
                        <button
                          disabled={busy}
                          onClick={() =>
                            window.confirm(
                              "Suspend every associated source, including shared sources?",
                            ) &&
                            action(() =>
                              post("/integrations/" + row.id + "/suspend", {
                                confirmed: true,
                                expected_revision: row.revision,
                              }),
                            )
                          }
                        >
                          Suspend
                        </button>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!list.items.length && (
            <p>
              No integrations match this organization/filter. Existing V1.5
              resources remain below.
            </p>
          )}
          <div className="row-actions">
            <button
              disabled={!offset}
              onClick={() => setOffset((v) => Math.max(0, v - 25))}
            >
              Previous
            </button>
            <span>{list.total} integrations</span>
            <button
              disabled={offset + 25 >= list.total}
              onClick={() => setOffset((v) => v + 25)}
            >
              Next
            </button>
          </div>
        </div>
      )}
      {editing && (
        <section ref={wizardRef} aria-label="Data Pipelines eight-step wizard">
          <div className="page-heading">
            <h3>{editing.id ? editing.name : "New Data Pipeline"}</h3>
            <button onClick={() => setEditing(null)}>
              Close configuration
            </button>
          </div>
          {Object.entries(editing.pagination || {}).some(
            ([, page]) => page.has_more,
          ) && (
            <p role="status">
              Partial integration preview:{" "}
              {Object.entries(editing.pagination || {})
                .filter(([, page]) => page.has_more)
                .map(([name, page]) => `${name} ${page.limit} of ${page.total}`)
                .join("; ")}
              .
              {editing.readiness_complete === false &&
                " Activation readiness is incomplete in this preview."}
            </p>
          )}
          <nav className="pipeline-steps" aria-label="Data Pipeline steps">
            {PIPELINE_STEPS.map((label, i) => (
              <button
                key={label}
                aria-current={step === i + 1 ? "step" : undefined}
                className={step === i + 1 ? "active" : ""}
                onClick={() => setStep(i + 1)}
              >
                {i + 1}. {label}
              </button>
            ))}
          </nav>
          {step === 1 && (
            <div className="form-grid">
              <Field label="Integration name">
                <input
                  value={draft.name}
                  disabled={!allowed || Boolean(editing.enabled)}
                  onChange={(e) =>
                    setDraft((v) => ({ ...v, name: e.target.value }))
                  }
                />
              </Field>
              <Field label="Organization">
                <select
                  value={draft.organization_id}
                  disabled={!allowed || Boolean(parent) || Boolean(editing.id)}
                  onChange={(e) =>
                    setDraft((v) => ({ ...v, organization_id: e.target.value }))
                  }
                >
                  <option value="">Select organization</option>
                  {customers.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </Field>
              <Field label="Environment">
                <select
                  value={draft.environment}
                  disabled={!allowed || Boolean(parent) || Boolean(editing.id)}
                  onChange={(e) =>
                    setDraft((v) => ({ ...v, environment: e.target.value }))
                  }
                >
                  {["PROD", "QA", "TEST", "DEV", "SANDBOX"].map((e) => (
                    <option key={e}>{e}</option>
                  ))}
                </select>
              </Field>
              <Field label="Compute Instance (optional)">
                <select
                  disabled={!allowed || Boolean(editing.id)}
                  value={draft.vm_resource_id}
                  onChange={(e) => parentChange(e.target.value)}
                >
                  <option value="">SaaS / no local Compute Instance</option>
                  {vms.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.name} · {v.environment}
                    </option>
                  ))}
                </select>
              </Field>
              {parent && (
                <p className="muted">
                  Organization and environment are inherited. Existing VM
                  installation and HOSTED_ON relationships are preserved.
                </p>
              )}
            </div>
          )}
          {step === 2 && (
            <>
              <Field label="Platform family">
                <select
                  disabled={!allowed || Boolean(editing.id)}
                  value={draft.platform}
                  onChange={(e) => {
                    setDraft((v) => ({ ...v, platform: e.target.value }));
                    setConnection({});
                  }}
                >
                  {catalogue?.platforms.map((p) => (
                    <option key={p.platform}>{p.platform}</option>
                  ))}
                </select>
              </Field>
              <p>
                Compatibility is unverified until genuine installed-version and
                collection evidence are independently reviewed.
              </p>
              <ul>
                {selectedPlatform?.versions.map((v) => (
                  <li key={v.version}>
                    {v.version} · catalogue candidate · {v.compatibility}
                  </li>
                ))}
              </ul>
            </>
          )}
          {step === 3 && (
            <>
              <DynamicConfigurationForm
                definition={"PLATFORM_" + draft.platform}
                value={connection}
                onChange={setConnection}
                disabled={!allowed}
              />
              <p className="muted">
                Provision connection secrets on the backend using customer-bound
                references:{" "}
                <code>
                  {"env:OPSCONTROL_PIPELINE_SECRET_" +
                    draft.organization_id.replaceAll("-", "").toUpperCase() +
                    "_TOKEN"}
                </code>
                . Enter the reference only.
              </p>
              <button
                disabled={!allowed || busy || !editing.id}
                onClick={() =>
                  action(() =>
                    post("/integrations/" + editing.id + "/connections", {
                      configuration: connection,
                    }),
                  )
                }
              >
                Save connection version
              </button>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Version</th>
                      <th scope="col">Active</th>
                      <th scope="col">Checksum</th>
                      <th scope="col">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editing.connections.map((c) => (
                      <tr key={c.id}>
                        <td>{c.version}</td>
                        <td>{c.active ? "Yes" : "Saved, not applied"}</td>
                        <td className="mono">{c.checksum}</td>
                        <td>{c.created_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p>
                Managed secret references only. Saving makes no live connection
                request.
              </p>
            </>
          )}
          {step === 4 && (
            <>
              <div className="form-grid">
                {["platform_version", "edition", "deployment_type"].map((k) => (
                  <Field key={k} label={k.replaceAll("_", " ")}>
                    <input
                      value={profile[k]}
                      disabled={!allowed}
                      onChange={(e) =>
                        setProfile((v) => ({ ...v, [k]: e.target.value }))
                      }
                    />
                  </Field>
                ))}
              </div>
              <Field label="Documented collection capabilities">
                <select
                  value={profile.supported_methods[0]}
                  onChange={(e) =>
                    setProfile((v) => ({
                      ...v,
                      supported_methods: [e.target.value],
                    }))
                  }
                  disabled={!allowed}
                >
                  {["PLATFORM_API", "FILE_LOG", "DATABASE"].map((m) => (
                    <option key={m}>{m}</option>
                  ))}
                </select>
              </Field>
              <button
                disabled={!allowed || busy || !editing.id}
                onClick={() =>
                  action(() =>
                    post(
                      "/integrations/" + editing.id + "/capabilities",
                      profile,
                    ),
                  )
                }
              >
                Save capability profile
              </button>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Installed version</th>
                      <th scope="col">Edition</th>
                      <th scope="col">Compatibility</th>
                      <th scope="col">Evidence</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editing.capabilities.map((c) => (
                      <tr key={c.id}>
                        <td>{c.platform_version}</td>
                        <td>{c.edition}</td>
                        <td>{c.compatibility}</td>
                        <td>{c.evidence_status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {step === 5 && (
            <>
              <div className="form-grid">
                <Field label="Collection method name">
                  <input
                    value={method.name}
                    disabled={!allowed}
                    onChange={(e) =>
                      setMethod((v) => ({ ...v, name: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Collection method type">
                  <select
                    value={method.method_type}
                    onChange={(e) =>
                      setMethod((v) => ({ ...v, method_type: e.target.value }))
                    }
                  >
                    {["PLATFORM_API", "FILE_LOG", "DATABASE"].map((m) => (
                      <option key={m}>{m}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Collection transport">
                  <select
                    value={method.transport}
                    onChange={(e) =>
                      setMethod((v) => ({ ...v, transport: e.target.value }))
                    }
                  >
                    <option>BACKEND</option>
                    <option>AGENT</option>
                  </select>
                </Field>
                {(method.method_type === "FILE_LOG"
                  ? ["path"]
                  : ["endpoint", "account", "physical_scope"]
                ).map((k) => (
                  <Field key={k} label={"Source " + k.replaceAll("_", " ")}>
                    <input
                      value={method.identity[k] || ""}
                      onChange={(e) =>
                        setMethod((v) => ({
                          ...v,
                          identity: { ...v.identity, [k]: e.target.value },
                        }))
                      }
                    />
                  </Field>
                ))}
                <Field label="Collection interval seconds">
                  <input
                    type="number"
                    min="5"
                    max="3600"
                    value={method.configuration.interval_seconds || 60}
                    onChange={(e) =>
                      setMethod((v) => ({
                        ...v,
                        configuration: {
                          ...v.configuration,
                          interval_seconds: Number(e.target.value),
                        },
                      }))
                    }
                  />
                </Field>
              </div>
              <button
                disabled={
                  !allowed ||
                  busy ||
                  !editing.id ||
                  !activeConnection ||
                  !activeProfile
                }
                onClick={() => action(addMethod)}
              >
                Add collection method
              </button>
              <p className="muted">
                Identical sources are reused. A paused integration suspends
                shared sources. Overlapping file patterns remain independent.
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Method</th>
                      <th scope="col">Transport</th>
                      <th scope="col">Validation</th>
                      <th scope="col">Health / coverage</th>
                      <th scope="col">Generation / fence</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editing.methods.map((m) => {
                      const source = editing.sources.find(
                        (s) => s.id === m.source_id,
                      );
                      return (
                        <tr key={m.id}>
                          <td>
                            {m.name}
                            <small>{m.configuration.method_type}</small>
                          </td>
                          <td>{m.transport}</td>
                          <td>{m.validation}</td>
                          <td>
                            {source?.health || "NO_DATA"} ·{" "}
                            {m.enabled ? "Enabled" : "Disabled"}
                          </td>
                          <td className="mono">
                            {source?.generation} / {source?.fence}
                          </td>
                          <td>
                            <button
                              disabled={!allowed || busy}
                              onClick={() =>
                                action(() =>
                                  control(api + "/methods/" + m.id, "PUT", {
                                    name: m.name,
                                    enabled: !m.enabled,
                                    expected_revision: m.revision,
                                    idempotency_key: key(),
                                  }),
                                )
                              }
                            >
                              {m.enabled ? "Disable" : "Enable"}
                            </button>
                            <button
                              disabled={!allowed || busy}
                              onClick={() =>
                                action(() =>
                                  post("/methods/" + m.id + "/validate"),
                                )
                              }
                            >
                              Validate
                            </button>
                            <button
                              disabled={!allowed || busy}
                              onClick={() =>
                                window.confirm(
                                  "Retire this method and retain its evidence?",
                                ) &&
                                action(() =>
                                  control(api + "/methods/" + m.id, "DELETE", {
                                    confirmed: true,
                                    idempotency_key: key(),
                                  }),
                                )
                              }
                            >
                              Retire
                            </button>
                            <button
                              onClick={() =>
                                action(async () => {
                                  const impact = await control(
                                    api + "/sources/" + m.source_id + "/impact",
                                  );
                                  window.alert(JSON.stringify(impact, null, 2));
                                })
                              }
                            >
                              Impact
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {(step === 6 || step === 7) && (
            <div className="row-actions">
              <Field label="Search native jobs">
                <input
                  value={jobSearch}
                  onChange={(e) => {
                    setJobSearch(e.target.value);
                    setJobOffset(0);
                    setAssociation((v) => ({ ...v, job_id: "" }));
                  }}
                />
              </Field>
              <button
                disabled={jobOffset === 0 || busy}
                onClick={() => setJobOffset((v) => Math.max(0, v - 50))}
              >
                Previous jobs
              </button>
              <span>
                {jobPage
                  ? `${jobPage.total} ${step === 7 ? "selected " : ""}jobs · page ${Math.floor(jobOffset / 50) + 1}`
                  : "Loading jobs…"}
              </span>
              <button
                disabled={!jobPage || jobOffset + 50 >= jobPage.total || busy}
                onClick={() => setJobOffset((v) => v + 50)}
              >
                Next jobs
              </button>
            </div>
          )}
          {step === 6 && (
            <>
              <div className="row-actions">
                <button
                  disabled={!allowed || busy || !editing.id}
                  onClick={() =>
                    action(() =>
                      post("/integrations/" + editing.id + "/discovery"),
                    )
                  }
                >
                  Discover jobs on demand
                </button>
                <button
                  disabled={!allowed || busy || !editing.id}
                  onClick={() =>
                    action(() =>
                      post("/integrations/" + editing.id + "/redetection"),
                    )
                  }
                >
                  Redetect platform
                </button>
              </div>
              <p>
                Global discovery: every 24 hours. Platform redetection: every
                seven days. Read-only discovery requires an authorized
                connection. Collection remains blocked until runtime
                verification.
              </p>
              <div className="form-grid">
                <Field label="Stable native job ID">
                  <input
                    value={job.native_id}
                    onChange={(e) =>
                      setJob((v) => ({ ...v, native_id: e.target.value }))
                    }
                  />
                </Field>
                <Field label="Job display name">
                  <input
                    value={job.name}
                    onChange={(e) =>
                      setJob((v) => ({ ...v, name: e.target.value }))
                    }
                  />
                </Field>
              </div>
              <button
                disabled={
                  !allowed || busy || !editing.id || !job.native_id || !job.name
                }
                onClick={() =>
                  action(() =>
                    post("/integrations/" + editing.id + "/jobs", job),
                  )
                }
              >
                Register job manually
              </button>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Job</th>
                      <th scope="col">Native identity</th>
                      <th scope="col">Selection</th>
                      <th scope="col">Discovery / staleness</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(jobPage?.items || []).map((j) => (
                      <tr key={j.id}>
                        <td>
                          {j.resource_id ? (
                            <button
                              onClick={() =>
                                onResourceSelected?.(j.resource_id)
                              }
                            >
                              {j.name}
                            </button>
                          ) : (
                            j.name
                          )}
                        </td>
                        <td className="mono">{j.native_id}</td>
                        <td>{j.selected ? "Selected" : "Not selected"}</td>
                        <td>
                          {j.quarantined
                            ? "Quarantined"
                            : j.stale_since
                              ? "Stale; selected jobs protected"
                              : j.origin}
                        </td>
                        <td>
                          <button
                            disabled={!allowed || busy || j.quarantined}
                            onClick={() =>
                              window.confirm(
                                (j.selected ? "Deselect" : "Select") +
                                  " native job " +
                                  j.native_id +
                                  "?",
                              ) &&
                              action(() =>
                                post("/jobs/" + j.id + "/selection", {
                                  selected: !j.selected,
                                  confirmed: true,
                                  expected_revision: j.revision,
                                }),
                              )
                            }
                          >
                            {j.selected ? "Deselect" : "Select explicitly"}
                          </button>
                          {j.quarantined && j.origin === "MANUAL" && (
                            <button
                              disabled={!allowed || busy}
                              onClick={() =>
                                window.confirm(
                                  "Confirm this exact manual/discovered identity? Names alone are insufficient.",
                                ) &&
                                action(() =>
                                  post(
                                    "/jobs/" +
                                      j.id +
                                      "/confirm-discovered-identity",
                                    { confirmed: true },
                                  ),
                                )
                              }
                            >
                              Confirm discovered identity
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {step === 7 && (
            <>
              <div className="form-grid">
                <Field label="Job association">
                  <select
                    value={association.job_id}
                    onChange={(e) =>
                      setAssociation((v) => ({ ...v, job_id: e.target.value }))
                    }
                  >
                    <option value="">Select job</option>
                    {(jobPage?.items || []).map((j) => (
                      <option key={j.id} value={j.id}>
                        {j.name} · {j.native_id}
                      </option>
                    ))}
                  </select>
                </Field>
                <Field label="Source association">
                  <select
                    value={association.method_id}
                    onChange={(e) =>
                      setAssociation((v) => ({
                        ...v,
                        method_id: e.target.value,
                      }))
                    }
                  >
                    <option value="">
                      Select independent collection method
                    </option>
                    {editing.methods.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name}
                      </option>
                    ))}
                  </select>
                </Field>
              </div>
              <button
                disabled={
                  !allowed ||
                  busy ||
                  !association.job_id ||
                  !association.method_id
                }
                onClick={() =>
                  window.confirm(
                    "Confirm source-to-job routing? This creates no execution dependency.",
                  ) &&
                  action(() =>
                    post("/integrations/" + editing.id + "/associations", {
                      ...association,
                      confirmed: true,
                    }),
                  )
                }
              >
                Confirm source association
              </button>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th scope="col">Job</th>
                      <th scope="col">Method</th>
                      <th scope="col">Confirmation</th>
                      <th scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {editing.associations.map((a) => (
                      <tr key={a.id}>
                        <td>
                          {editing.jobs.find((j) => j.id === a.job_id)?.name}
                        </td>
                        <td>
                          {
                            editing.methods.find((m) => m.id === a.method_id)
                              ?.name
                          }
                        </td>
                        <td>{a.created_at}</td>
                        <td>
                          <button
                            disabled={!allowed || busy}
                            onClick={() =>
                              window.confirm(
                                "Remove this routing association?",
                              ) &&
                              action(() =>
                                control(
                                  api + "/associations/" + a.id,
                                  "DELETE",
                                  { confirmed: true, idempotency_key: key() },
                                ),
                              )
                            }
                          >
                            Remove
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
          {step === 8 && (
            <>
              <h4>Backend activation eligibility</h4>
              {blockers.length ? (
                <ul>
                  {blockers.map((b) => (
                    <li key={b}>{b}</li>
                  ))}
                </ul>
              ) : (
                <p>
                  Validate the current persisted configuration before
                  activation. No health is inferred from saved fields.
                </p>
              )}
              <button
                disabled={busy || !editing.id}
                onClick={() =>
                  action(() =>
                    post("/integrations/" + editing.id + "/validate"),
                  )
                }
              >
                Validate configuration
              </button>
              <button
                className="primary-button"
                disabled={
                  !allowed || busy || !editing.id || Boolean(blockers.length)
                }
                onClick={() =>
                  window.confirm(
                    "Activate only independently verified collection sources?",
                  ) &&
                  action(() =>
                    post("/integrations/" + editing.id + "/activate", {
                      confirmed: true,
                      expected_revision: editing.revision,
                    }),
                  )
                }
              >
                Activate monitoring
              </button>
              <details>
                <summary>Durable operations and configuration history</summary>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th scope="col">Operation</th>
                        <th scope="col">Status</th>
                        <th scope="col">Evidence / blockers</th>
                      </tr>
                    </thead>
                    <tbody>
                      {editing.operations.map((o) => (
                        <tr key={o.id}>
                          <td>{o.kind}</td>
                          <td>{o.state}</td>
                          <td>
                            <pre>{JSON.stringify(o.result, null, 2)}</pre>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </details>
            </>
          )}
          <div className="form-footer">
            <button
              disabled={step === 1 || busy}
              onClick={() => setStep((v) => v - 1)}
            >
              Back
            </button>
            <button
              disabled={
                !allowed || busy || !draft.name || !draft.organization_id
              }
              onClick={save}
            >
              Save / resume draft
            </button>
            <button
              disabled={step === 8 || busy}
              onClick={() => setStep((v) => v + 1)}
            >
              Next
            </button>
            <span>
              {step} / 8 · {editing.id || "Draft not yet persisted"}
            </span>
          </div>
        </section>
      )}
    </section>
  );
}
