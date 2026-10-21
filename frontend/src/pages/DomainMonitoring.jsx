import { useState } from "react";
import { control } from "../controlPlane";
import { query, useNativeFeed } from "./UnifiedOverview";
import { ConditionTable, Verification } from "./UnifiedResourceManagement";
import LegacyVMHealth from "./VMHealth";
import LegacyAPIs from "./APIs";
import ETLJobs from "./ETLJobs";
const names = {
  VM: "Compute Health",
  API: "API Endpoint Monitoring",
  ETL: "Data Pipeline Monitoring",
};
export default function DomainMonitoring({
  domain,
  organizationIds,
  environment,
  jobs = [],
  loading,
  error,
  onSelectExecution,
  onNavigate,
  initialResourceId,
}) {
  const [offset, setOffset] = useState(0),
    [selected, setSelected] = useState(initialResourceId || null),
    [history, setHistory] = useState(null),
    [detailError, setDetailError] = useState(""),
    [compat, setCompat] = useState(true);
  const feed = useNativeFeed(
    "/api/v1/unified/domain-state/" +
      domain +
      "?" +
      query(organizationIds, environment, { limit: 50, offset }),
  );
  const show = async (r) => {
    setSelected(r.id);
    setHistory(null);
    setDetailError("");
    if (domain === "ETL")
      try {
        setHistory(
          await control("/api/v1/unified/resources/" + r.id + "/executions"),
        );
      } catch (e) {
        setDetailError(e.message);
      }
  };
  const row = feed.data?.items.find((r) => r.id === selected);
  return (
    <div className="domain-monitoring">
      <div className="page-heading">
        <div>
          <h1>{names[domain]}</h1>
          <p>Observed status, independent conditions and source evidence.</p>
        </div>
        <button onClick={feed.refresh}>Refresh</button>
      </div>
      {feed.error && <p role="alert">{feed.error}</p>}
      {!feed.data && !feed.error && <p>Loading monitored resources…</p>}
      {domain !== "ETL" && (
        <section className="domain-adapter-primary" aria-label={domain === "VM" ? "Infrastructure adapter evidence" : "Service probe evidence"}>
          <button type="button" className="filter-button" aria-expanded={compat} onClick={() => setCompat((value) => !value)}>
            {compat ? "Hide" : "Show"} {domain === "VM" ? "infrastructure adapter health" : "service probe health"}
          </button>
          {compat && (domain === "VM"
            ? <LegacyVMHealth embedded organizationIds={organizationIds} environment={environment} />
            : <LegacyAPIs embedded organizationIds={organizationIds} environment={environment} onNavigate={onNavigate} />)}
        </section>
      )}
      {domain !== "ETL" && <h2>Registered monitoring resource context</h2>}
      <section className="card table-wrap">
        <table>
          <thead>
            <tr>
              <th>Resource</th>
              <th>Customer / environment</th>
              <th>Monitoring</th>
              <th>Observed state</th>
              <th>Last evidence</th>
              <th>Alerts</th>
            </tr>
          </thead>
          <tbody>
            {feed.data?.items.map((r) => (
              <tr key={r.id}>
                <td>
                  <button
                    className="resource-name-link"
                    onClick={() => show(r)}
                  >
                    {r.name}
                  </button>
                  <small>{r.id}</small>
                </td>
                <td>
                  {r.inherited.customer}
                  <small>{r.environment}</small>
                </td>
                <td>{r.activation_status}</td>
                <td>
                  {domain === "ETL"
                    ? r.latest_execution?.status || "No execution evidence"
                    : r.operational_state}
                  {domain === "ETL" &&
                    r.latest_execution?.monitoring_conditions && (
                      <small>
                        {Object.entries(
                          r.latest_execution.monitoring_conditions,
                        )
                          .filter(([, active]) => active)
                          .map(([name]) => name)
                          .join(", ")}
                      </small>
                    )}
                </td>
                <td>
                  {domain === "ETL"
                    ? r.latest_execution?.source_evidence?.observed_at ||
                      "Unknown"
                    : domain === "API"
                      ? r.latest_probe?.ended_at || "Unknown"
                      : r.source_verification.last_received_at || "Unknown"}
                </td>
                <td>
                  <button
                    onClick={() =>
                      onNavigate("Alerts", { domain, resourceId: r.id })
                    }
                  >
                    {r.conditions.filter((c) => c.active).length}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {feed.data && !feed.data.items.length && (
          <p>No resources in this authorized customer/environment scope.</p>
        )}
      </section>
      {feed.data && (
        <div className="form-footer">
          <span>{feed.data.total} resources</span>
          <button
            disabled={!offset}
            onClick={() => setOffset((v) => Math.max(0, v - 50))}
          >
            Previous
          </button>
          <button
            disabled={!feed.data.has_more}
            onClick={() => setOffset((v) => v + 50)}
          >
            Next
          </button>
        </div>
      )}
      {row && (
        <section className="card" aria-label="Monitoring resource details">
          <div className="page-heading">
            <h2>{row.name}</h2>
            <button onClick={() => setSelected(null)}>Close details</button>
          </div>
          <Verification data={row.source_verification} />
          <ConditionTable rows={row.conditions} />
          {domain === "VM" && (
            <div className="table-wrap">
              <h3>Latest actual metrics</h3>
              <table>
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Value / unit</th>
                    <th>Dimensions</th>
                    <th>Observed</th>
                  </tr>
                </thead>
                <tbody>
                  {row.latest_metrics.map((m) => (
                    <tr key={m.metric_definition_id}>
                      <td>{m.name}</td>
                      <td>
                        {m.value} {m.unit}
                      </td>
                      <td>
                        <code>{JSON.stringify(m.dimensions)}</code>
                      </td>
                      <td>{m.observed_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!row.latest_metrics.length && (
                <p>No received metric evidence.</p>
              )}
            </div>
          )}
          {domain === "API" && (
            <>
              <h3>Last probe evidence</h3>
              {row.latest_probe ? (
                <pre>{JSON.stringify(row.latest_probe, null, 2)}</pre>
              ) : (
                <p>No completed probe.</p>
              )}
            </>
          )}
          {domain === "ETL" && (
            <>
              <h3>Execution history and steps</h3>
              {detailError && <p role="alert">{detailError}</p>}
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Execution / Order ID</th>
                      <th>Terminal/runtime status</th>
                      <th>Conditions</th>
                      <th>Start / end</th>
                      <th>Step attempts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history?.items.map((h) => (
                      <tr key={h.id}>
                        <td>
                          <button onClick={() => onSelectExecution(h.id)}>
                            {h.provider_execution_id || h.id}
                          </button>
                        </td>
                        <td>{h.status}</td>
                        <td>
                          {Object.entries(h.monitoring_conditions || {})
                            .filter(([, v]) => v)
                            .map(([k]) => k)
                            .join(", ") || "None recorded"}
                        </td>
                        <td>
                          {h.started_at || "Unknown"}
                          <small>{h.ended_at || "No terminal evidence"}</small>
                        </td>
                        <td>
                          <details>
                            <summary>{h.steps.length} step attempts</summary>
                            <table>
                              <thead>
                                <tr>
                                  <th>Step</th>
                                  <th>Attempt</th>
                                  <th>Status</th>
                                  <th>Duration</th>
                                </tr>
                              </thead>
                              <tbody>
                                {h.steps.map((s) => (
                                  <tr key={s.id}>
                                    <td>{s.name}</td>
                                    <td>{s.attempt}</td>
                                    <td>{s.status}</td>
                                    <td>
                                      {s.duration_seconds == null
                                        ? "Unknown"
                                        : s.duration_seconds + " s"}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </details>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <h3>Expected execution windows</h3>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Scheduled</th>
                      <th>Deadline</th>
                      <th>Condition</th>
                      <th>Execution</th>
                    </tr>
                  </thead>
                  <tbody>
                    {row.schedule_windows.map((w) => (
                      <tr key={w.id}>
                        <td>{w.scheduled_at}</td>
                        <td>{w.deadline}</td>
                        <td>{w.status}</td>
                        <td>{w.history_id || "No execution observed"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </section>
      )}
      {domain === "ETL" && (
        <section className="card">
          <h2>Execution investigation</h2>
          <ETLJobs
            embedded
            jobs={jobs}
            loading={loading}
            error={error}
            onSelect={onSelectExecution}
            onRetry={feed.refresh}
          />
        </section>
      )}
    </div>
  );
}
