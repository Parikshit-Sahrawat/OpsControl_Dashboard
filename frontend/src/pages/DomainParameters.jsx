import {
  useEffect,
  useState,
  useRef,
  Children,
  isValidElement,
  cloneElement,
} from "react";
import { control, downloadText } from "../controlPlane";
import DynamicConfigurationForm from "../components/DynamicConfigurationForm";
import { hasPermission } from "../permissions";
export const defaults = (domain, r) =>
  domain === "ETL"
    ? {
        domain,
        duplicate_matching: {
          cross_source: true,
          attributes: ["execution_id", "jobchain"],
          conflict_resolution: "RETAIN_UNKNOWN",
          source_precedence: [],
        },
        parser: r?.configuration?.parser || {
          format: "JSON",
          field_mapping: {
            execution_id: "execution_id",
            event_type: "event",
            status: "status",
            step_name: "step",
            timestamp: "timestamp",
          },
          status_mapping: {
            RUNNING: "RUNNING",
            SUCCESS: "SUCCESS",
            FAILED: "FAILED",
          },
          timezone: "UTC",
          execution_identity_fields: ["execution_id", "order_id"],
        },
        schedule: r?.configuration?.schedule || null,
        no_run_grace_seconds: 900,
        delayed_start_seconds: 120,
        long_running_seconds: 3600,
        no_response_seconds: 300,
        completion_sla_seconds: 7200,
        require_dependencies: true,
        overrides: {},
      }
    : domain === "VM"
      ? {
          domain,
          thresholds: [],
          services: r?.configuration?.services || [],
          processes: r?.configuration?.processes || [],
          missing_telemetry_seconds: 120,
          service_failures: 2,
          overrides: {},
        }
      : {
          domain,
          expected_statuses: [200],
          warning_latency_ms: 1000,
          critical_latency_ms: 3000,
          consecutive_failures: 2,
          recovery_successes: 2,
          missing_results_seconds: 120,
          availability_percent: 99.9,
          sla_window_minutes: 1440,
          overrides: {},
        };
export function Field({ label, children }) {
  return (
    <label className="form-field">
      <span>{label}</span>
      {Children.map(children, (child) =>
        isValidElement(child) &&
        ["input", "select", "textarea"].includes(child.type)
          ? cloneElement(child, {
              "aria-label": child.props["aria-label"] || label,
            })
          : child,
      )}
    </label>
  );
}
export default function DomainParameters({ resource, user, onSaved }) {
  const [data, setData] = useState(null),
    [config, setConfig] = useState(defaults(resource.domain, resource)),
    [preview, setPreview] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [approved, setApproved] = useState(false),
    [metrics, setMetrics] = useState([]),
    [selectedMetric, setSelectedMetric] = useState(""),
    [threshold, setThreshold] = useState(80),
    [importText, setImportText] = useState(""),
    [importFormat, setImportFormat] = useState("YAML");
  const editorRef = useRef(null);
  const ensureValid = () => {
    if (editorRef.current?.querySelector('[aria-invalid="true"]'))
      throw Error("Correct invalid JSON before preview or saving");
  };
  const can = hasPermission(user, "templates.manage", resource.organization_id),
    prefix = "/api/v1/unified/parameters/" + resource.id;
  useEffect(() => {
    let live = true;
    setError("");
    setPreview(null);
    setData(null);
    setConfig(defaults(resource.domain, resource));
    Promise.all([
      control(prefix),
      control("/api/v1/unified/resources/" + resource.id + "/metrics"),
    ])
      .then(([v, m]) => {
        if (!live) return;
        setData(v);
        setMetrics(m);
        const p =
          v.versions.find((p) => p.status === "ACTIVE") || v.versions[0];
        if (p) setConfig(p.configuration);
      })
      .catch((e) => live && setError(e.message));
    return () => {
      live = false;
    };
  }, [resource.id, resource.revision]);
  const change = (key, value) => {
    setConfig((c) => ({ ...c, [key]: value }));
    setPreview(null);
    setApproved(false);
  };
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
  const makePreview = () =>
    action(async () => {
      ensureValid();
      setPreview(
        await control(prefix + "/preview", "POST", {
          expected_resource_revision: resource.revision,
          configuration: config,
        }),
      );
    });
  const save = (activate) =>
    action(async () => {
      ensureValid();
      if (activate && !approved)
        throw Error(
          "Review the effective configuration and approve activation",
        );
      const p = await control(prefix, "POST", {
        expected_resource_revision: resource.revision,
        configuration: config,
      });
      if (activate)
        await control(prefix + "/activate", "POST", {
          version: p.version,
          approve: true,
        });
      setData(await control(prefix));
      setApproved(false);
      await onSaved?.(p);
    });
  const schedule = config.schedule;
  return (
    <section ref={editorRef} className="card unified-parameters">
      <h3>
        {resource.domain === "ETL"
          ? "Data Pipeline"
          : resource.domain === "VM"
            ? "Compute Health"
            : "API Endpoint"}{" "}
        Parameters · {resource.name}
      </h3>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data && <p>Loading parameter history…</p>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Inherited attribute</th>
              <th>Value</th>
              <th>Provenance</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(data?.inherited || resource.inherited || {}).map(
              ([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td>
                    {Array.isArray(v) ? v.join(", ") : String(v ?? "Unmapped")}
                  </td>
                  <td>INHERITED · read only</td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>
      <DynamicConfigurationForm
        definition={"PARAM_" + resource.domain}
        value={config}
        disabled={!can}
        onChange={setConfig}
        keys={
          resource.domain === "ETL"
            ? [
                "no_run_grace_seconds",
                "delayed_start_seconds",
                "long_running_seconds",
                "no_response_seconds",
                "completion_sla_seconds",
                "duplicate_matching",
              ]
            : resource.domain === "VM"
              ? ["missing_telemetry_seconds", "service_failures"]
              : [
                  "expected_statuses",
                  "warning_latency_ms",
                  "critical_latency_ms",
                  "consecutive_failures",
                  "recovery_successes",
                  "missing_results_seconds",
                  "availability_percent",
                  "sla_window_minutes",
                ]
        }
      />
      {resource.domain === "ETL" && (
        <>
          <div className="form-grid">
            <Field label="Expected schedule">
              <select
                disabled={!can}
                value={schedule?.frequency || "NONE"}
                onChange={(e) =>
                  change(
                    "schedule",
                    e.target.value === "NONE"
                      ? null
                      : {
                          frequency: e.target.value,
                          time: "00:00",
                          timezone: "UTC",
                          weekdays: [0, 1, 2, 3, 4, 5, 6],
                          month_day: 1,
                          exceptions: [],
                          dst_policy: "FIRST",
                          catchup_hours: 24,
                        },
                  )
                }
              >
                <option value="NONE">No expected schedule</option>
                {[
                  "HOURLY",
                  "DAILY",
                  "WEEKLY",
                  "MONTHLY",
                  "QUARTERLY",
                  "CUSTOM",
                ].map((v) => (
                  <option key={v}>{v}</option>
                ))}
              </select>
            </Field>
          </div>
          {schedule && (
            <div className="form-grid">
              <Field label="Schedule time">
                <input
                  type="time"
                  value={schedule.time}
                  disabled={!can}
                  onChange={(e) =>
                    change("schedule", { ...schedule, time: e.target.value })
                  }
                />
              </Field>
              <Field label="Schedule timezone">
                <input
                  value={schedule.timezone}
                  disabled={!can}
                  onChange={(e) =>
                    change("schedule", {
                      ...schedule,
                      timezone: e.target.value,
                    })
                  }
                />
              </Field>
              {schedule.frequency === "CUSTOM" && (
                <Field label="Cron expression">
                  <input
                    value={schedule.cron || ""}
                    placeholder="0 9 * * 1-5"
                    disabled={!can}
                    onChange={(e) =>
                      change("schedule", { ...schedule, cron: e.target.value })
                    }
                  />
                </Field>
              )}
              {schedule.frequency === "WEEKLY" && (
                <Field label="Weekdays (Monday=0)">
                  <input
                    value={schedule.weekdays.join(",")}
                    disabled={!can}
                    onChange={(e) =>
                      change("schedule", {
                        ...schedule,
                        weekdays: e.target.value.split(",").map(Number),
                      })
                    }
                  />
                </Field>
              )}
              {["MONTHLY", "QUARTERLY"].includes(schedule.frequency) && (
                <Field label="Day of month">
                  <input
                    type="number"
                    min="1"
                    max="31"
                    value={schedule.month_day}
                    disabled={!can}
                    onChange={(e) =>
                      change("schedule", {
                        ...schedule,
                        month_day: Number(e.target.value),
                      })
                    }
                  />
                </Field>
              )}
              <Field label="Schedule exceptions (ISO dates)">
                <textarea
                  value={(schedule.exceptions || []).join("\n")}
                  disabled={!can}
                  onChange={(e) =>
                    change("schedule", {
                      ...schedule,
                      exceptions: e.target.value.split("\n").filter(Boolean),
                    })
                  }
                />
              </Field>
              <Field label="DST repeated-time policy">
                <select
                  value={schedule.dst_policy || "FIRST"}
                  disabled={!can}
                  onChange={(e) =>
                    change("schedule", {
                      ...schedule,
                      dst_policy: e.target.value,
                    })
                  }
                >
                  <option>FIRST</option>
                  <option>SECOND</option>
                </select>
              </Field>
            </div>
          )}
          <div className="form-grid">
            <Field label="Log parser">
              <select
                value={config.parser.format}
                disabled={!can}
                onChange={(e) =>
                  change("parser", { ...config.parser, format: e.target.value })
                }
              >
                <option>JSON</option>
                <option>REGEX</option>
              </select>
            </Field>
            {config.parser.format === "REGEX" && (
              <Field label="Log pattern">
                <input
                  value={config.parser.pattern || ""}
                  disabled={!can}
                  onChange={(e) =>
                    change("parser", {
                      ...config.parser,
                      pattern: e.target.value,
                    })
                  }
                />
              </Field>
            )}
            <Field label="Timestamp format (optional)">
              <input
                value={config.parser.timestamp_format || ""}
                disabled={!can}
                onChange={(e) =>
                  change("parser", {
                    ...config.parser,
                    timestamp_format: e.target.value || null,
                  })
                }
              />
            </Field>
            <Field label="Parser timezone">
              <input
                value={config.parser.timezone}
                disabled={!can}
                onChange={(e) =>
                  change("parser", {
                    ...config.parser,
                    timezone: e.target.value,
                  })
                }
              />
            </Field>
          </div>
          <JsonField
            label="Execution field mapping"
            value={config.parser.field_mapping}
            disabled={!can}
            onChange={(v) =>
              change("parser", { ...config.parser, field_mapping: v })
            }
          />
          <JsonField
            label="Execution status mapping"
            value={config.parser.status_mapping}
            disabled={!can}
            onChange={(v) =>
              change("parser", { ...config.parser, status_mapping: v })
            }
          />
          <JsonField
            label="Step/event mapping"
            value={config.parser.event_mapping || {}}
            disabled={!can}
            onChange={(v) =>
              change("parser", { ...config.parser, event_mapping: v })
            }
          />
          <label>
            <input
              type="checkbox"
              checked={config.require_dependencies}
              disabled={!can}
              onChange={(e) => change("require_dependencies", e.target.checked)}
            />{" "}
            Evaluate declared dependencies
          </label>
        </>
      )}
      {resource.domain === "VM" && (
        <>
          <div className="form-grid">
            <Field label="Monitored services (one per line)">
              <textarea
                value={(config.services || []).join("\n")}
                disabled={!can}
                onChange={(e) =>
                  change("services", e.target.value.split("\n").filter(Boolean))
                }
              />
            </Field>
            <Field label="Monitored processes (one per line)">
              <textarea
                value={(config.processes || []).join("\n")}
                disabled={!can}
                onChange={(e) =>
                  change(
                    "processes",
                    e.target.value.split("\n").filter(Boolean),
                  )
                }
              />
            </Field>
          </div>
          <p className="muted">
            Service/process collection belongs to the VM configuration.
            Monitoring parameters reference those configured identities.
          </p>
          <div className="form-grid">
            <Field label="Observed metric">
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
              >
                <option value="">Select actual telemetry</option>
                {metrics.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} ({m.unit || "unknown unit"}) ·{" "}
                    {JSON.stringify(m.dimensions)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Critical threshold">
              <input
                type="number"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
              />
            </Field>
          </div>
          <button
            className="filter-button"
            disabled={!can || !selectedMetric}
            onClick={() => {
              const m = metrics.find((m) => m.id === selectedMetric);
              change("thresholds", [
                ...config.thresholds,
                {
                  metric_name: m.name,
                  metric_definition_id: m.id,
                  operator: "GT",
                  critical: threshold,
                  unit: m.unit,
                  duration_seconds: 60,
                  consecutive_breaches: 2,
                  maximum_gap_seconds: 90,
                  threshold_mode: "STATIC",
                },
              ]);
            }}
          >
            Add metric threshold
          </button>
          <JsonField
            label="Metric rules — units, windows, recovery and dynamic thresholds"
            value={config.thresholds}
            disabled={!can}
            onChange={(v) => change("thresholds", v)}
          />
        </>
      )}
      <JsonField
        label="Explicit rule overrides"
        value={config.overrides || {}}
        disabled={!can}
        onChange={(v) => change("overrides", v)}
      />
      <details>
        <summary>Import YAML/JSON configuration</summary>
        <Field label="Configuration file">
          <input
            type="file"
            accept=".yaml,.yml,.json"
            disabled={!can}
            onChange={async (e) => {
              try {
                const file = e.target.files[0];
                if (!file) return;
                if (file.size > 262144) throw Error("File exceeds 256 KiB");
                setImportText(await file.text());
                setImportFormat(file.name.endsWith(".json") ? "JSON" : "YAML");
              } catch (error) {
                setError(error.message);
              }
            }}
          />
        </Field>
        <button
          disabled={!importText || busy}
          onClick={() =>
            action(async () => {
              const v = await control(prefix + "/import", "POST", {
                expected_resource_revision: resource.revision,
                format: importFormat,
                content: importText,
                save: false,
              });
              setConfig(v.configuration);
              setPreview(v);
              setApproved(false);
            })
          }
        >
          Validate and preview import
        </button>
      </details>
      <div className="form-footer">
        <button className="filter-button" disabled={busy} onClick={makePreview}>
          Preview effective configuration
        </button>
        <button
          className="filter-button"
          onClick={() =>
            downloadText(
              resource.domain.toLowerCase() + "-parameters.json",
              JSON.stringify(config, null, 2),
            )
          }
        >
          Download JSON
        </button>
        <button disabled={busy || !can} onClick={() => save(false)}>
          Save version
        </button>
      </div>
      {preview && (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Attribute</th>
                  <th>Effective value</th>
                  <th>Provenance</th>
                </tr>
              </thead>
              <tbody>
                {preview.attributes.map((a) => (
                  <tr key={a.name}>
                    <td>{a.name}</td>
                    <td>
                      <code>
                        {typeof a.value === "object"
                          ? JSON.stringify(a.value)
                          : String(a.value ?? "Unmapped")}
                      </code>
                    </td>
                    <td>{a.provenance}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <label>
            <input
              type="checkbox"
              checked={approved}
              disabled={!can}
              onChange={(e) => setApproved(e.target.checked)}
            />{" "}
            Approve this validated parameter configuration
          </label>
          <button
            className="primary-button"
            disabled={!can || !approved || busy}
            onClick={() => save(true)}
          >
            Save and activate parameters
          </button>
          <p className="muted">
            Parameter activation does not install an agent or prove telemetry
            reception.
          </p>
        </>
      )}
      <h4>Version history</h4>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Version</th>
              <th>Status</th>
              <th>Created</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {data?.versions.map((p) => (
              <tr key={p.id}>
                <td>{p.version}</td>
                <td>{p.status}</td>
                <td>{new Date(p.created_at).toISOString()}</td>
                <td>
                  <button
                    onClick={() => {
                      setConfig(p.configuration);
                      setPreview(null);
                      setApproved(false);
                    }}
                  >
                    Review version
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!data?.versions.length && <p>No saved versions.</p>}
    </section>
  );
}
export function JsonField({ label, value, onChange, disabled = false }) {
  const [text, setText] = useState(JSON.stringify(value, null, 2)),
    [error, setError] = useState("");
  useEffect(
    () => setText(JSON.stringify(value, null, 2)),
    [JSON.stringify(value)],
  );
  return (
    <Field label={label}>
      <textarea
        rows="5"
        className="configuration-preview"
        value={text}
        disabled={disabled}
        onChange={(e) => {
          setText(e.target.value);
          try {
            onChange(JSON.parse(e.target.value));
            setError("");
          } catch {
            setError("Enter valid JSON");
          }
        }}
        aria-invalid={!!error}
      />
      {error && <small role="alert">{error}</small>}
    </Field>
  );
}
