import { useEffect, useRef, useState } from "react";
import {
  control,
  downloadText,
  downloadPackage,
  packageAvailability,
  methodDefaults,
} from "../controlPlane";
import { createCollector, updateCollector } from "../resourceApi";
import useDialogFocus from "../components/useDialogFocus";
import DynamicConfigurationForm from "../components/DynamicConfigurationForm";
import { hasPermission } from "../permissions";
function Field({ label, children }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      {children}
    </label>
  );
}
export default function CollectorControl({
  collector,
  sources,
  user,
  onClose,
  onSaved,
}) {
  const [snapshot, setSnapshot] = useState(null),
    [name, setName] = useState(collector?.name || ""),
    [sourceId, setSourceId] = useState(
      collector?.data_source_id || sources[0]?.id || "",
    ),
    [method, setMethod] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [yaml, setYaml] = useState(""),
    [token, setToken] = useState(""),
    [packages, setPackages] = useState(null),
    [packageError, setPackageError] = useState(""),
    [osMetrics, setOsMetrics] = useState(false);
  const [approved, setApproved] = useState(false);
  const [templateDefaults, setTemplateDefaults] = useState(null);
  const ref = useRef(null);
  useDialogFocus(ref, true, onClose);
  const source = sources.find((s) => s.id === sourceId);
  const can = hasPermission(user, "collectors.manage", source?.organization_id);
  const prefix = "/api/v1/agent-control/collectors/" + collector?.id;
  const refresh = async () => {
    const data = await control(prefix);
    setSnapshot(data);
  };
  useEffect(() => {
    let live = true;
    if (collector?.id)
      control(prefix)
        .then((v) => {
          if (live) {
            setSnapshot(v);
            setOsMetrics(Boolean(v.collector.configuration?.os_metrics));
          }
        })
        .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [collector?.id]);
  const checkPackages = async () => {
    try {
      const availability = await packageAvailability();
      setPackages(availability);
      setPackageError("");
    } catch (e) {
      setPackageError(e.message);
    }
  };
  useEffect(() => {
    checkPackages();
  }, []);
  const downloadAgent = (platform) =>
    action(async () => {
      await downloadPackage(platform);
      await checkPackages();
    });
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
  const change = (key, value) =>
    setMethod((m) => ({
      ...m,
      configuration: { ...m.configuration, [key]: value },
    }));
  const saveMethod = () =>
    action(async () => {
      if (ref.current?.querySelector('[aria-invalid="true"]'))
        throw new Error("Correct invalid collection attributes before saving");
      await control(
        prefix + "/methods" + (method.id ? "/" + method.id : ""),
        method.id ? "PUT" : "POST",
        {
          name: method.name,
          method_type: method.method_type,
          configuration: method.configuration,
          enabled: method.enabled,
          ...(method.id ? { expected_revision: method.revision } : {}),
        },
      );
      setMethod(null);
      await refresh();
    });
  const create = () =>
    action(async () => {
      if (!sourceId || !name.trim())
        throw new Error("Name and Data Source required");
      await createCollector({
        data_source_id: sourceId,
        name: name.trim(),
        collector_type: "OTEL",
        enabled: true,
        interval_seconds: 30,
        configuration: { os_metrics: osMetrics },
      });
      await onSaved();
      onClose();
    });
  const cfg = method?.configuration || {};
  return (
    <div className="modal-backdrop">
      <section
        className="modal resource-onboarding-modal"
        ref={ref}
        role="dialog"
        aria-modal="true"
        aria-label={collector ? "Collector Details" : "Create Collector"}
      >
        <div className="modal-header">
          <h2>{collector ? "Collector Details" : "Create Collector"}</h2>
          <button
            aria-label="Close Collector Details"
            disabled={busy}
            onClick={onClose}
          >
            ×
          </button>
        </div>
        {error && <p role="alert">{error}</p>}
        {!collector ? (
          <div className="resource-form">
            <Field label="Collector name">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
              />
            </Field>
            <Field label="Data Source">
              <select
                value={sourceId}
                onChange={(e) => setSourceId(e.target.value)}
              >
                {sources.map((s) => (
                  <option value={s.id} key={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </Field>
            <p>
              OS Type inherited from Data Source:{" "}
              {source?.connection_config?.opscontrol?.os_type || "Unsupported"}
            </p>
            <label>
              <input
                type="checkbox"
                checked={osMetrics}
                onChange={(e) => setOsMetrics(e.target.checked)}
              />{" "}
              OS Metrics (native hostmetrics)
            </label>
            <button
              className="primary-button"
              disabled={busy || !can}
              onClick={create}
            >
              Create Collector
            </button>
          </div>
        ) : snapshot ? (
          <>
            <div className="form-grid">
              <Field label="Collector name">
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </Field>
              <label>
                <input
                  type="checkbox"
                  checked={osMetrics}
                  onChange={(e) => setOsMetrics(e.target.checked)}
                />{" "}
                OS Metrics (native hostmetrics)
              </label>
            </div>
            <button
              disabled={busy || !can}
              onClick={() =>
                action(async () => {
                  await updateCollector(collector.id, {
                    name,
                    configuration: {
                      ...snapshot.collector.configuration,
                      os_metrics: osMetrics,
                    },
                  });
                  await refresh();
                  onSaved();
                })
              }
            >
              Save Collector Details
            </button>
            <p>
              Inherited OS: {snapshot.os_type} · OTel Contrib{" "}
              {snapshot.runtime_version}
            </p>
            <section>
              <button
                disabled={!can || busy}
                onClick={() =>
                  action(async () => {
                    await updateCollector(collector.id, {
                      enabled: !snapshot.collector.enabled,
                    });
                    await refresh();
                    onSaved();
                  })
                }
              >
                {snapshot.collector.enabled
                  ? "Disable Collector"
                  : "Enable Collector"}
              </button>
              <h3>Agent Health</h3>
              <p>
                {snapshot.agent
                  ? `${snapshot.agent.connection} · reported runtime ${snapshot.agent.health} · Agent Version ${snapshot.agent.version}`
                  : "NOT REGISTERED"}
              </p>
              {snapshot.agent?.last_error && (
                <p role="alert">{snapshot.agent.last_error}</p>
              )}
              <h3>Telemetry Pipeline Health</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Signal</th>
                      <th>State</th>
                      <th>Received count</th>
                      <th>Last received</th>
                    </tr>
                  </thead>
                  <tbody>
                    {["logs", "metrics", "traces"].map((signal) => {
                      const row = snapshot.signals.find(
                        (s) => s.signal === signal,
                      );
                      return (
                        <tr key={signal}>
                          <td>{signal}</td>
                          <td>{row?.status || "NO_DATA"}</td>
                          <td>{row?.count || 0}</td>
                          <td>{row?.last_received_at || "Never"}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
            <section>
              <div className="resource-toolbar">
                <h3>Collection Methods</h3>
                <button
                  disabled={
                    busy ||
                    !hasPermission(
                      user,
                      "templates.view",
                      source?.organization_id,
                    )
                  }
                  onClick={() =>
                    action(async () =>
                      setTemplateDefaults(
                        await control(prefix + "/template-defaults"),
                      ),
                    )
                  }
                >
                  Use Template Defaults
                </button>
                <button
                  disabled={busy || !can}
                  onClick={() =>
                    setMethod({
                      name: "",
                      method_type: "FILE_LOG",
                      configuration: { ...methodDefaults.FILE_LOG },
                      enabled: true,
                    })
                  }
                >
                  Add Method
                </button>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Type</th>
                      <th>Signals</th>
                      <th>Enabled</th>
                      <th>Validation / configuration state</th>
                      <th>Revision</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.methods.map((m) => (
                      <tr key={m.id}>
                        <td>{m.name}</td>
                        <td>{m.method_type}</td>
                        <td>
                          {["FILE_LOG", "SYSLOG_RECEIVER"].includes(
                            m.method_type,
                          )
                            ? "Logs"
                            : [
                                  "METRIC_SCRAPE",
                                  "HOST_METRICS",
                                  "SERVICES",
                                ].includes(m.method_type)
                              ? "Metrics"
                              : m.configuration.signals.join(", ")}
                        </td>
                        <td>{m.enabled ? "Yes" : "No"}</td>
                        <td>
                          {m.validation_status} · {m.binary_validation}
                          <small>
                            {m.deployment_status} ·{" "}
                            {m.collection_status || "NO_DATA"}
                          </small>
                          <small>
                            {m.record_count || 0} records · last receipt{" "}
                            {m.last_received_at || "Never"}
                          </small>
                          {m.method_observation?.error_code && (
                            <small role="alert">
                              {m.method_observation.error_code}
                            </small>
                          )}
                        </td>
                        <td>{m.revision}</td>
                        <td>
                          <button
                            disabled={!can || busy}
                            onClick={() => setMethod(structuredClone(m))}
                          >
                            Edit
                          </button>
                          <button
                            disabled={!can || busy}
                            onClick={() =>
                              action(async () => {
                                await control(
                                  prefix + "/methods/" + m.id,
                                  "PUT",
                                  {
                                    name: m.name,
                                    method_type: m.method_type,
                                    configuration: m.configuration,
                                    enabled: !m.enabled,
                                    expected_revision: m.revision,
                                  },
                                );
                                await refresh();
                              })
                            }
                          >
                            {m.enabled ? "Disable" : "Enable"}
                          </button>
                          <button
                            disabled={!can || busy}
                            onClick={() => {
                              if (
                                window.confirm(
                                  "Delete this method from future configuration revisions? Existing deployed revisions remain unchanged.",
                                )
                              )
                                action(async () => {
                                  await control(
                                    prefix + "/methods/" + m.id,
                                    "DELETE",
                                  );
                                  await refresh();
                                });
                            }}
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!snapshot.methods.length && (
                  <p>No collection methods configured.</p>
                )}
              </div>
              {templateDefaults && (
                <div className="builder-section">
                  <h4>Attached template drafts</h4>
                  {templateDefaults.methods.map((preset, i) => (
                    <button
                      key={i}
                      disabled={!can || busy}
                      onClick={() => setMethod(structuredClone(preset))}
                    >
                      Configure {preset.name}
                    </button>
                  ))}
                  {!templateDefaults.methods.length && (
                    <p>
                      No compatible resolved log defaults. Add a method
                      explicitly.
                    </p>
                  )}
                  {templateDefaults.warnings.map((message, i) => (
                    <p role="alert" key={i}>
                      {message}
                    </p>
                  ))}
                  <p>
                    Defaults are drafts. Review host paths and save each method
                    explicitly.
                  </p>
                </div>
              )}
              {method && (
                <div className="builder-section resource-form">
                  <h4>{method.id ? "Edit Method" : "Add Method"}</h4>
                  <Field label="Method name">
                    <input
                      value={method.name}
                      onChange={(e) =>
                        setMethod((m) => ({ ...m, name: e.target.value }))
                      }
                    />
                  </Field>
                  <Field label="Method type">
                    <select
                      disabled={Boolean(method.id)}
                      value={method.method_type}
                      onChange={(e) =>
                        setMethod((m) => ({
                          ...m,
                          method_type: e.target.value,
                          configuration: structuredClone(
                            methodDefaults[e.target.value],
                          ),
                        }))
                      }
                    >
                      {Object.keys(methodDefaults).map((type) => (
                        <option key={type} value={type}>
                          {
                            {
                              HOST_METRICS: "Host Metrics",
                              SERVICES: "Services",
                              SYSLOG_RECEIVER: "Syslog",
                              FILE_LOG: "File Logs",
                              METRIC_SCRAPE: "OpsControl Scrape",
                              OTLP_RECEIVER:
                                "OTLP Receiver (advanced transport)",
                            }[type]
                          }
                        </option>
                      ))}
                    </select>
                  </Field>
                  <DynamicConfigurationForm
                    definition={method.method_type}
                    context={{ os_type: snapshot.os_type }}
                    value={cfg}
                    disabled={!can}
                    onChange={(configuration) =>
                      setMethod((m) => ({ ...m, configuration }))
                    }
                  />
                  {method.method_type === "FILE_LOG" && (
                    <p>
                      Source identifiers and persistent file-storage checkpoints
                      survive compatible configuration changes. The Agent
                      reports permissions, tailing and rotation failures.
                    </p>
                  )}
                  {method.method_type === "OTLP_RECEIVER" && (
                    <p>
                      Configure application instrumentation for this listener's
                      explicit protocol and selected signals. Remote listeners
                      require approved TLS/authentication; saving does not prove
                      reception.
                    </p>
                  )}
                  <div className="row-actions">
                    <button
                      disabled={busy || !method.name.trim()}
                      onClick={saveMethod}
                    >
                      Save Method
                    </button>
                    <button disabled={busy} onClick={() => setMethod(null)}>
                      Cancel Method
                    </button>
                  </div>
                </div>
              )}
            </section>
            <section>
              <h3>Collector Configuration</h3>
              <div className="row-actions">
                <button
                  onClick={() =>
                    action(async () =>
                      setYaml((await control(prefix + "/preview")).yaml),
                    )
                  }
                >
                  Preview YAML
                </button>
                <button
                  disabled={!yaml}
                  onClick={() => downloadText("opscontrol-otel.yaml", yaml)}
                >
                  Download YAML
                </button>
                <button
                  disabled={!can || busy}
                  onClick={() =>
                    action(async () => {
                      await control(prefix + "/versions", "POST");
                      await refresh();
                    })
                  }
                >
                  Save / Validate Revision
                </button>
              </div>
              {yaml && <pre className="configuration-preview">{yaml}</pre>}
              <label>
                <input
                  type="checkbox"
                  checked={approved}
                  onChange={(e) => setApproved(e.target.checked)}
                />
                I approve applying the selected configuration to this host.
              </label>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Revision</th>
                      <th>Collector validation</th>
                      <th>Created</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {snapshot.versions.map((v) => (
                      <tr key={v.id}>
                        <td>{v.revision}</td>
                        <td>{v.validation_status}</td>
                        <td>{v.created_at}</td>
                        <td>
                          <button
                            disabled={
                              !can ||
                              !approved ||
                              busy ||
                              v.validation_status !== "VALIDATED" ||
                              !snapshot.agent?.enabled
                            }
                            onClick={() =>
                              action(async () => {
                                await control(prefix + "/apply", "POST", {
                                  revision: v.revision,
                                  approve: true,
                                });
                                await refresh();
                              })
                            }
                          >
                            {snapshot.agent?.applied_revision === v.revision
                              ? "Reapply Configuration"
                              : "Apply Configuration"}
                          </button>
                          <button
                            onClick={() =>
                              downloadText(
                                "opscontrol-revision-" + v.revision + ".yaml",
                                v.yaml_text,
                              )
                            }
                          >
                            Download
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h4>Deployment History / Rollback</h4>
              {snapshot.deployments.length ? (
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Revision</th>
                        <th>Previous revision</th>
                        <th>Status</th>
                        <th>Approved</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.deployments.map((d) => (
                        <tr key={d.id}>
                          <td>{d.revision}</td>
                          <td>{d.previous_revision ?? "None"}</td>
                          <td>{d.status}</td>
                          <td>{d.created_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>
                  No configuration deployments. Saving YAML is not deployment.
                </p>
              )}
              <p>
                Rollback: explicitly approve an earlier validated revision.
                APPLIED is an agent report; telemetry reception is tracked
                separately.
              </p>
            </section>
            <section>
              <h3>Agent Installation</h3>
              <p>
                Install the approved OpsControl Agent on the target host before
                generating a 15-minute enrollment token. Installation and
                secure registration are separate steps.
              </p>
              {packageError && <p role="alert">{packageError}</p>}
              <div className="row-actions">
                <button type="button" onClick={checkPackages} disabled={busy}>
                  Check installer availability
                </button>
                <button
                  type="button"
                  disabled={busy || !packages?.linux?.available}
                  onClick={() => downloadAgent("linux")}
                >
                  Download Linux Agent (.zip)
                </button>
                <button
                  type="button"
                  disabled={busy || !packages?.windows?.available}
                  onClick={() => downloadAgent("windows")}
                >
                  Download Windows Installer (.exe)
                </button>
              </div>
              {packages && (
                <div aria-live="polite">
                  <p>Linux: {packages.linux?.available ? "Approved package available" : "Installer not provisioned"}</p>
                  <p>Windows: {packages.windows?.available ? "Approved installer available" : "Installer not provisioned"}</p>
                </div>
              )}
              <p>
                When an installer is unavailable, an administrator must publish
                the verified package to the configured agent package directory.
                Do not use the configuration YAML as an installer.
              </p>
              <p>
                Copyable target-host download links require a separately authorized,
                short-lived download credential. Your dashboard login token must
                never be copied into a URL or shell command.
              </p>
              <a
                href="https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/main/docs/AGENT_INSTALL_OPERATOR.md"
                target="_blank"
                rel="noreferrer"
              >
                Agent installation guide — Linux and Windows
              </a>
              <h3>Agent Registration</h3>
              <button
                disabled={
                  !can ||
                  busy ||
                  snapshot.os_type === "Unsupported" ||
                  snapshot.agent?.enabled
                }
                onClick={() =>
                  action(async () =>
                    setToken(
                      (await control(prefix + "/registration", "POST"))
                        .enrollment_token,
                    ),
                  )
                }
              >
                Create one-time enrollment
              </button>
              {token && (
                <>
                  <p>
                    Copy once to the target's protected enrollment file. Expires
                    in 15 minutes.
                  </p>
                  <code className="enrollment-secret">{token}</code>
                  <button onClick={() => setToken("")}>
                    Clear enrollment token
                  </button>
                </>
              )}
              {snapshot.agent?.enabled && (
                <button
                  disabled={!can || busy}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Revoke agent authentication and stop accepting telemetry?",
                      )
                    )
                      action(async () => {
                        await control(prefix + "/agent", "DELETE");
                        await refresh();
                      });
                  }}
                >
                  Revoke Agent
                </button>
              )}
            </section>
          </>
        ) : (
          <p>Loading Collector Details…</p>
        )}
      </section>
    </div>
  );
}
