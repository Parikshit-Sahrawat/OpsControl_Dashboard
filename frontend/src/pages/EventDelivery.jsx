import { useEffect, useRef, useState } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
export default function EventDelivery({ kind, organizations, user }) {
  const [org, setOrg] = useState(organizations[0]?.id || ""),
    [data, setData] = useState(null),
    [metrics, setMetrics] = useState([]),
    [destinations, setDestinations] = useState([]),
    [draft, setDraft] = useState(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [preview, setPreview] = useState(null);
  const epoch = useRef(0);
  const events = kind === "events",
    path = "/api/v1/" + (events ? "event-parameters" : "notification-delivery");
  const can = hasPermission(user, "templates.manage", org);
  const load = async () => {
    const version = ++epoch.current;
    setData(null);
    try {
      const [result, m, d] = await Promise.all([
        control(path + "?organization_id=" + org),
        events
          ? control("/api/v1/event-parameters/metrics?organization_id=" + org)
          : [],
        events
          ? control("/api/v1/notification-delivery?organization_id=" + org)
          : null,
      ]);
      if (version === epoch.current) {
        setData(result);
        setMetrics(m);
        setDestinations(d?.destinations || []);
      }
    } catch (e) {
      if (version === epoch.current) setError(e.message);
    }
  };
  useEffect(() => {
    if (org) load();
    setDraft(null);
    setError("");
    return () => {
      epoch.current++;
    };
  }, [org, kind, user?.authorization_revision]);
  const change = (key, value) => setDraft((d) => ({ ...d, [key]: value }));
  const create = () =>
    setDraft(
      events
        ? {
            organization_id: org,
            name: "",
            metric_definition_id: "",
            threshold_percentage: 80,
            time_window_minutes: 5,
            minimum_event_count: 2,
            maximum_sample_gap_seconds: 90,
            threshold_mode: "STATIC",
            baseline_minutes: 60,
            baseline_minimum_samples: 30,
            standard_deviations: 3,
            severity: "WARNING",
            description: "",
            destinations: [],
            classes: [],
            types: [],
            components: [],
            enabled: true,
          }
        : {
            organization_id: org,
            name: "",
            channel: "IN_APP",
            configuration: {},
            enabled: true,
          },
    );
  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { id, ...payload } = draft;
      await control(path + (id ? "/" + id : ""), id ? "PUT" : "POST", payload);
      setDraft(null);
      setPreview(null);
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };
  const config = (key, value) =>
    change("configuration", { ...draft.configuration, [key]: value });
  return (
    <section className="card resource-section-stack">
      <div className="resource-toolbar">
        <h2>{events ? "Event Parameters" : "Notification Delivery"}</h2>
        <button disabled={!can || busy} onClick={create}>
          Create {events ? "Event Parameter" : "Destination"}
        </button>
      </div>
      <label className="form-field">
        <span>Organization</span>
        <select value={org} onChange={(e) => setOrg(e.target.value)}>
          {organizations.map((o) => (
            <option key={o.id} value={o.id}>
              {o.name}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      {!org && <p>No authorized organizations.</p>}
      {data ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>{events ? "Parameter / threshold" : "Channel"}</th>
                <th>Enabled</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {(events ? data : data.destinations).map((row) => (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>
                    {events
                      ? `${row.evaluation_config.threshold_mode} · ${row.threshold_value}% · ${row.evaluation_config.time_window_minutes} min`
                      : row.channel}
                  </td>
                  <td>{row.enabled ? "Yes" : "No"}</td>
                  <td>
                    <button
                      disabled={!can}
                      onClick={() =>
                        setDraft(
                          events
                            ? { ...row.evaluation_config, id: row.id }
                            : {
                                id: row.id,
                                organization_id: row.organization_id,
                                name: row.name,
                                channel: row.channel,
                                configuration: row.configuration,
                                enabled: row.enabled,
                              },
                        )
                      }
                    >
                      Edit
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {!(events ? data : data.destinations).length && (
            <p>No {events ? "event parameters" : "destinations"} configured.</p>
          )}
        </div>
      ) : (
        org && <p>Loading configuration…</p>
      )}
      {draft && (
        <form className="resource-form builder-section" onSubmit={save}>
          <h3>
            {draft.id ? "Edit" : "Create"}{" "}
            {events ? "Event Parameter" : "Destination"}
          </h3>
          <label className="form-field">
            <span>Name</span>
            <input
              required
              value={draft.name}
              onChange={(e) => change("name", e.target.value)}
            />
          </label>
          <label>
            <input
              type="checkbox"
              checked={draft.enabled}
              onChange={(e) => change("enabled", e.target.checked)}
            />{" "}
            Enabled
          </label>
          {events ? (
            <>
              <label className="form-field">
                <span>Parameter selection (stored percentage metrics)</span>
                <select
                  required
                  value={draft.metric_definition_id}
                  onChange={(e) =>
                    change("metric_definition_id", e.target.value)
                  }
                >
                  <option value="">Select metric</option>
                  {metrics
                    .filter((m) => m.unit === "%")
                    .map((m) => (
                      <option value={m.id} key={m.id}>
                        {m.name} · %
                      </option>
                    ))}
                </select>
              </label>
              <label className="form-field">
                <span>Description</span>
                <input
                  value={draft.description}
                  onChange={(e) => change("description", e.target.value)}
                />
              </label>
              <div className="form-grid">
                {[
                  ["threshold_percentage", "Threshold percentage"],
                  ["time_window_minutes", "Time window (minutes)"],
                  ["minimum_event_count", "Minimum event count"],
                  [
                    "maximum_sample_gap_seconds",
                    "Maximum sample gap (seconds)",
                  ],
                ].map(([key, label]) => (
                  <label className="form-field" key={key}>
                    <span>{label}</span>
                    <input
                      required
                      type="number"
                      value={draft[key]}
                      onChange={(e) => change(key, Number(e.target.value))}
                    />
                  </label>
                ))}
              </div>
              <label className="form-field">
                <span>Condition</span>
                <select
                  value={draft.operator || "GT"}
                  onChange={(e) => change("operator", e.target.value)}
                >
                  {["GT", "GTE", "LT", "LTE"].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </label>
              <label className="form-field">
                <span>Threshold mode</span>
                <select
                  value={draft.threshold_mode}
                  onChange={(e) => change("threshold_mode", e.target.value)}
                >
                  {["STATIC", "DYNAMIC", "COMBINED"].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </label>
              {draft.threshold_mode !== "STATIC" && (
                <div className="form-grid">
                  {[
                    ["baseline_minutes", "Baseline minutes"],
                    ["baseline_minimum_samples", "Minimum baseline samples"],
                    ["standard_deviations", "Standard deviations"],
                  ].map(([key, label]) => (
                    <label className="form-field" key={key}>
                      <span>{label}</span>
                      <input
                        type="number"
                        step="any"
                        value={draft[key]}
                        onChange={(e) => change(key, Number(e.target.value))}
                      />
                    </label>
                  ))}
                </div>
              )}
              <label className="form-field">
                <span>Severity</span>
                <select
                  value={draft.severity}
                  onChange={(e) => change("severity", e.target.value)}
                >
                  {["INFO", "WARNING", "CRITICAL"].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </label>
              {["classes", "types", "components"].map((key) => (
                <label className="form-field" key={key}>
                  <span>{key}</span>
                  <input
                    value={draft[key].join(", ")}
                    onChange={(e) =>
                      change(
                        key,
                        e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter(Boolean),
                      )
                    }
                  />
                </label>
              ))}
              <label className="form-field">
                <span>Notification services</span>
                <div className="check-grid">
                  {destinations
                    .filter((d) => d.enabled)
                    .map((d) => (
                      <label key={d.id}>
                        <input
                          type="checkbox"
                          checked={draft.destinations.includes(d.id)}
                          onChange={(e) =>
                            change(
                              "destinations",
                              e.target.checked
                                ? [...draft.destinations, d.id]
                                : draft.destinations.filter(
                                    (id) => id !== d.id,
                                  ),
                            )
                          }
                        />
                        {d.name}
                      </label>
                    ))}
                </div>
              </label>
              <p>
                Aggregation: every consecutive sample must satisfy the condition
                across the full window. Missing/gapped data cannot prove a
                sustained breach.
              </p>
              <button
                type="button"
                disabled={!draft.metric_definition_id || busy}
                onClick={async () => {
                  try {
                    const { id, ...body } = draft;
                    setPreview(
                      await control(
                        "/api/v1/event-parameters/preview",
                        "POST",
                        body,
                      ),
                    );
                  } catch (e) {
                    setError(e.message);
                  }
                }}
              >
                Preview stored telemetry
              </button>
              {preview && <pre>{JSON.stringify(preview, null, 2)}</pre>}
            </>
          ) : (
            <>
              <label className="form-field">
                <span>Channel</span>
                <select
                  value={draft.channel}
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      channel: e.target.value,
                      configuration: {},
                    }))
                  }
                >
                  {["IN_APP", "SMTP", "WEBHOOK"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </label>
              {draft.channel === "WEBHOOK" && (
                <label className="form-field">
                  <span>HTTPS webhook URL</span>
                  <input
                    required
                    value={draft.configuration.url || ""}
                    onChange={(e) => config("url", e.target.value)}
                  />
                </label>
              )}
              {draft.channel === "SMTP" && (
                <>
                  {[
                    ["host", "SMTP host"],
                    ["sender", "Sender address"],
                  ].map(([key, label]) => (
                    <label className="form-field" key={key}>
                      <span>{label}</span>
                      <input
                        required
                        value={draft.configuration[key] || ""}
                        onChange={(e) => config(key, e.target.value)}
                      />
                    </label>
                  ))}
                  <label className="form-field">
                    <span>Secure SMTP port</span>
                    <select
                      value={draft.configuration.port || 587}
                      onChange={(e) => config("port", Number(e.target.value))}
                    >
                      <option>587</option>
                      <option>465</option>
                    </select>
                  </label>
                  <label className="form-field">
                    <span>Recipients (comma separated)</span>
                    <input
                      required
                      value={(draft.configuration.recipients || []).join(", ")}
                      onChange={(e) =>
                        config(
                          "recipients",
                          e.target.value
                            .split(",")
                            .map((s) => s.trim())
                            .filter(Boolean),
                        )
                      }
                    />
                  </label>
                </>
              )}
              {draft.channel !== "IN_APP" && (
                <label className="form-field">
                  <span>Credential reference (env:NAME)</span>
                  <input
                    value={draft.configuration.credential_ref || ""}
                    onChange={(e) =>
                      config("credential_ref", e.target.value || null)
                    }
                  />
                </label>
              )}
              <p>
                Network destinations require a deployment-owned hostname/CIDR
                allowlist. Saving a destination does not prove provider health.
              </p>
            </>
          )}
          <div className="row-actions">
            <button className="primary-button" disabled={busy || !can}>
              {busy ? "Saving…" : "Save"}
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={() => setDraft(null)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
      {!events && data && (
        <>
          <h3>Delivery tracking</h3>
          <p>
            Queue lag: {Math.round(data.queue_lag_seconds || 0)} seconds ·
            provider health is established by actual delivery outcomes.
          </p>
          <p>
            Exponential retry/backoff with fenced leases and stable delivery
            identities. SMS/voice, Slack, Teams and push: unavailable until
            configured adapters exist.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Event</th>
                  <th>Destination</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>Created</th>
                  <th>Sent</th>
                  <th>Error</th>
                </tr>
              </thead>
              <tbody>
                {data.deliveries.map((d) => (
                  <tr key={d.id}>
                    <td>{d.event_type}</td>
                    <td>{d.channel}</td>
                    <td>{d.status}</td>
                    <td>{d.attempts}</td>
                    <td>{d.created_at}</td>
                    <td>{d.sent_at || "Not delivered"}</td>
                    <td>{d.last_error || "None"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
