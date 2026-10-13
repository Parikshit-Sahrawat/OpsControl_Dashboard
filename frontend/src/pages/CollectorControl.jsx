import { useEffect, useRef, useState } from "react";
import {
  control,
  downloadText,
  downloadPackage,
  methodDefaults,
} from "../controlPlane";
import { createCollector, updateCollector } from "../resourceApi";
import useDialogFocus from "../components/useDialogFocus";
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
                          {m.method_type === "FILE_LOG"
                            ? "Logs"
                            : m.method_type === "METRIC_SCRAPE"
                              ? "Metrics"
                              : m.configuration.signals.join(", ")}
                        </td>
                        <td>{m.enabled ? "Yes" : "No"}</td>
                        <td>
                          {m.validation_status} · {m.binary_validation}
                          <small>{m.deployment_status}</small>
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
                        <option key={type}>{type}</option>
                      ))}
                    </select>
                  </Field>
                  {method.method_type === "FILE_LOG" && (
                    <>
                      <Field label="Log source">
                        <select
                          value={cfg.source}
                          onChange={(e) => change("source", e.target.value)}
                        >
                          <option>FILE</option>
                          {snapshot.os_type === "Linux" && (
                            <option>JOURNALD</option>
                          )}
                          {snapshot.os_type === "Windows" && (
                            <option>WINDOWS_EVENT</option>
                          )}
                        </select>
                      </Field>
                      {cfg.source === "FILE" ? (
                        <>
                          <Field label="Paths (one absolute path per line)">
                            <textarea
                              value={(cfg.paths || []).join("\n")}
                              onChange={(e) =>
                                change(
                                  "paths",
                                  e.target.value.split("\n").filter(Boolean),
                                )
                              }
                            />
                          </Field>
                          <Field label="Exclusions">
                            <textarea
                              value={(cfg.exclusions || []).join("\n")}
                              onChange={(e) =>
                                change(
                                  "exclusions",
                                  e.target.value.split("\n").filter(Boolean),
                                )
                              }
                            />
                          </Field>
                          <Field label="Format">
                            <select
                              value={cfg.format}
                              onChange={(e) => change("format", e.target.value)}
                            >
                              <option>TEXT</option>
                              <option>JSON</option>
                            </select>
                          </Field>
                          <Field label="Multiline start pattern (optional)">
                            <input
                              value={cfg.multiline_pattern || ""}
                              onChange={(e) =>
                                change(
                                  "multiline_pattern",
                                  e.target.value || null,
                                )
                              }
                            />
                          </Field>
                        </>
                      ) : (
                        cfg.source === "WINDOWS_EVENT" && (
                          <Field label="Windows channel">
                            <input
                              value={cfg.channel || "Application"}
                              onChange={(e) =>
                                change("channel", e.target.value)
                              }
                            />
                          </Field>
                        )
                      )}
                    </>
                  )}
                  {method.method_type === "METRIC_SCRAPE" && (
                    <>
                      <Field label="Targets (host:port, one per line)">
                        <textarea
                          value={cfg.targets.join("\n")}
                          onChange={(e) =>
                            change(
                              "targets",
                              e.target.value.split("\n").filter(Boolean),
                            )
                          }
                        />
                      </Field>
                      <Field label="Scrape interval (seconds)">
                        <input
                          type="number"
                          min="5"
                          value={cfg.interval_seconds}
                          onChange={(e) =>
                            change("interval_seconds", Number(e.target.value))
                          }
                        />
                      </Field>
                      <Field label="Metrics path">
                        <input
                          value={cfg.path}
                          onChange={(e) => change("path", e.target.value)}
                        />
                      </Field>
                      <label>
                        <input
                          type="checkbox"
                          checked={cfg.tls}
                          onChange={(e) => change("tls", e.target.checked)}
                        />
                        TLS
                      </label>
                      <Field label="Authentication reference (env:NAME)">
                        <input
                          value={cfg.credential_ref || ""}
                          onChange={(e) =>
                            change("credential_ref", e.target.value || null)
                          }
                        />
                      </Field>
                    </>
                  )}
                  {method.method_type === "OTLP_RECEIVER" && (
                    <>
                      <div className="form-grid">
                        <Field label="Endpoint/DNS binding">
                          <input
                            value={cfg.bind}
                            onChange={(e) => change("bind", e.target.value)}
                          />
                        </Field>
                        <Field label="Port">
                          <input
                            type="number"
                            value={cfg.port}
                            onChange={(e) =>
                              change("port", Number(e.target.value))
                            }
                          />
                        </Field>
                      </div>
                      <Field label="Protocol">
                        <select
                          value={cfg.protocol}
                          onChange={(e) => change("protocol", e.target.value)}
                        >
                          <option>HTTP</option>
                          <option>GRPC</option>
                        </select>
                      </Field>
                      <Field label="Explicit signals">
                        <div className="check-grid">
                          {["Logs", "Metrics", "Traces"].map((signal) => (
                            <label key={signal}>
                              <input
                                type="checkbox"
                                checked={cfg.signals.includes(signal)}
                                onChange={(e) =>
                                  change(
                                    "signals",
                                    e.target.checked
                                      ? [...cfg.signals, signal]
                                      : cfg.signals.filter((s) => s !== signal),
                                  )
                                }
                              />
                              {signal}
                            </label>
                          ))}
                        </div>
                      </Field>
                      <label>
                        <input
                          type="checkbox"
                          checked={cfg.allow_remote}
                          onChange={(e) =>
                            change("allow_remote", e.target.checked)
                          }
                        />
                        Allow remote applications (requires TLS and
                        authentication)
                      </label>
                      <Field label="TLS certificate path">
                        <input
                          value={cfg.tls_certificate || ""}
                          onChange={(e) =>
                            change("tls_certificate", e.target.value || null)
                          }
                        />
                      </Field>
                      <Field label="TLS private key path">
                        <input
                          value={cfg.tls_key_ref || ""}
                          onChange={(e) =>
                            change("tls_key_ref", e.target.value || null)
                          }
                        />
                      </Field>
                      <Field label="Authentication reference">
                        <input
                          value={cfg.credential_ref || ""}
                          onChange={(e) =>
                            change("credential_ref", e.target.value || null)
                          }
                        />
                      </Field>
                      <p>
                        Application instrumentation: set
                        OTEL_EXPORTER_OTLP_ENDPOINT to{" "}
                        {cfg.tls_certificate ? "https" : "http"}://{cfg.bind}:
                        {cfg.port}, select{" "}
                        {cfg.protocol === "HTTP" ? "http/protobuf" : "grpc"},
                        and enable only {cfg.signals.join(", ")}. Provision
                        application TLS/authentication for remote listeners.
                      </p>
                    </>
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
              <div className="row-actions">
                <button onClick={() => action(() => downloadPackage("linux"))}>
                  Download Linux Agent
                </button>
                <button
                  onClick={() => action(() => downloadPackage("windows"))}
                >
                  Download Windows Agent
                </button>
              </div>
              <p>
                Manual installation only. A host IP does not provide a secure
                remote management channel.
              </p>
              <a
                href="https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/feature/consolidated-manual-uat/agent/README.md"
                target="_blank"
                rel="noreferrer"
              >
                Deploy Agent — Windows / Linux manual installation guide
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
