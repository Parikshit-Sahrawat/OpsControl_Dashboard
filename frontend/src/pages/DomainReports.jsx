import { useEffect, useState } from "react";
import { control, downloadText } from "../controlPlane";
import { query, useNativeFeed } from "./UnifiedOverview";
const label = {
  ETL: "ETL Reports",
  VM: "VM Health Reports",
  API: "API Reports",
};
const number = (v) =>
  v == null
    ? "Unknown"
    : typeof v === "number"
      ? v.toLocaleString(undefined, { maximumFractionDigits: 3 })
      : String(v);
export default function DomainReports({
  organizationIds,
  environment,
  onSelectExecution,
}) {
  const [domain, setDomain] = useState("ETL"),
    [resource, setResource] = useState(""),
    [resources, setResources] = useState([]),
    [offset, setOffset] = useState(0),
    [status, setStatus] = useState(""),
    [start, setStart] = useState(() =>
      new Date(Date.now() - 7 * 86400000).toISOString().slice(0, 10),
    ),
    [end, setEnd] = useState(() => new Date().toISOString().slice(0, 10));
  useEffect(() => {
    let live = true;
    setResources([]);
    setResource("");
    setOffset(0);
    setStatus("");
    control(
      "/api/v1/unified/resources?" +
        query(organizationIds, environment, { domain, limit: 200 }),
    )
      .then((v) => live && setResources(v.items))
      .catch(() => live && setResources([]));
    return () => {
      live = false;
    };
  }, [domain, organizationIds.join(","), environment]);
  const q = query(organizationIds, environment, {
    start: start + "T00:00:00Z",
    end: new Date(
      new Date(end + "T00:00:00Z").getTime() + 86400000,
    ).toISOString(),
    limit: 50,
    offset,
  });
  const params = new URLSearchParams(q);
  if (resource) params.append("resource_id", resource);
  if (status) params.set("status", status);
  const { data, error, refresh } = useNativeFeed(
    "/api/v1/unified/reports/" + domain + "?" + params,
  );
  const summaryKeys =
    domain === "ETL"
      ? [
          "observed_executions",
          "completed",
          "success",
          "failed",
          "running",
          "no_run",
          "delayed",
          "long_running_episodes",
          "sla_compliance_percent",
          "average_duration_seconds",
        ]
      : domain === "API"
        ? [
            "completed_probes",
            "successful_probes",
            "http_errors",
            "timeouts",
            "average_latency_ms",
            "p95_latency_ms",
            "availability_percent",
          ]
        : ["samples", "metric_series", "last_observed"];
  const histogram = data?.histogram || [],
    countKey =
      domain === "ETL" ? "completed" : domain === "API" ? "probes" : "maximum",
    max = Math.max(1, ...histogram.map((b) => Number(b[countKey]) || 0));
  return (
    <div className="domain-reports">
      <div className="page-heading">
        <div>
          <h1>Reports</h1>
          <p>Persisted evidence · UTC date range · no-data is unknown</p>
        </div>
        <div className="heading-actions">
          <button onClick={refresh}>Refresh</button>
          <button
            disabled={!data}
            onClick={() =>
              downloadText(
                "opscontrol-" + domain.toLowerCase() + "-report.json",
                JSON.stringify(data, null, 2),
              )
            }
          >
            Export JSON
          </button>
        </div>
      </div>
      <div role="tablist" aria-label="Report domains">
        {["ETL", "VM", "API"].map((d) => (
          <button
            key={d}
            role="tab"
            aria-selected={domain === d}
            onClick={() => setDomain(d)}
          >
            {label[d]}
          </button>
        ))}
      </div>
      <div className="resource-toolbar">
        <label>
          Start date
          <input
            type="date"
            value={start}
            onChange={(e) => {
              if (e.target.value) {
                setStart(e.target.value);
                setOffset(0);
              }
            }}
          />
        </label>
        <label>
          End date
          <input
            type="date"
            value={end}
            onChange={(e) => {
              if (e.target.value) {
                setEnd(e.target.value);
                setOffset(0);
              }
            }}
          />
        </label>
        <label>
          Report resource
          <select
            value={resource}
            onChange={(e) => {
              setResource(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All authorized resources</option>
            {resources.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </label>
        {domain !== "VM" && (
          <label>
            Report status
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setOffset(0);
              }}
            >
              <option value="">All statuses</option>
              {(domain === "ETL"
                ? ["RUNNING", "SUCCESS", "FAILED", "UNKNOWN", "LONG_RUNNING"]
                : ["SUCCESS", "FAILED"]
              ).map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
        )}
      </div>
      {error && (
        <p role="alert" className="error-banner">
          {error}
        </p>
      )}
      {!data && !error && <p>Aggregating persisted monitoring data…</p>}
      <section className="card table-wrap">
        <h2>{label[domain]}</h2>
        <table>
          <thead>
            <tr>
              <th>Measure</th>
              <th>Observed value</th>
            </tr>
          </thead>
          <tbody>
            {summaryKeys.map((k) => (
              <tr key={k}>
                <td>{k.replaceAll("_", " ")}</td>
                <td className="metric-value">{number(data?.summary[k])}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted">
          {data?.summary.availability_denominator || data?.summary.uptime_note}
        </p>
      </section>
      <section className="card table-wrap">
        <h2>
          {domain === "ETL"
            ? "Completed execution histogram"
            : domain === "API"
              ? "Endpoint reliability and latency"
              : "Host metric history"}
        </h2>
        {histogram.length ? (
          <table>
            <thead>
              <tr>
                <th>UTC bucket</th>
                <th>{domain === "VM" ? "Metric" : "Observed count"}</th>
                <th>Trend</th>
                <th>Statistics</th>
              </tr>
            </thead>
            <tbody>
              {histogram.slice(0, 300).map((b, i) => (
                <tr key={i}>
                  <td>{b.day || b.hour}</td>
                  <td>{domain === "VM" ? b.name : number(b[countKey])}</td>
                  <td>
                    <div
                      className="report-bar"
                      role="img"
                      aria-label={"Observed " + number(b[countKey])}
                    >
                      <span
                        style={{
                          width:
                            Math.max(
                              0,
                              Math.min(
                                100,
                                (100 * (Number(b[countKey]) || 0)) / max,
                              ),
                            ) + "%",
                        }}
                      />
                    </div>
                  </td>
                  <td>
                    {domain === "ETL"
                      ? "Success " +
                        b.success +
                        " · Failed " +
                        b.failed +
                        " · " +
                        number(b.average_duration_seconds) +
                        " s"
                      : domain === "API"
                        ? "Success " +
                          b.success +
                          " · Average " +
                          number(b.average_latency_ms) +
                          " ms"
                        : number(b.minimum) +
                          " – " +
                          number(b.maximum) +
                          " " +
                          (b.unit || "") +
                          " · Average " +
                          number(b.average)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>No observations in this date range.</p>
        )}
        {histogram.length > 300 && (
          <p>
            Showing 300 aggregated buckets; export includes the returned
            aggregation.
          </p>
        )}
      </section>
      {domain === "ETL" && (
        <section className="card table-wrap">
          <h2>Step failure analysis</h2>
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Failed attempts</th>
              </tr>
            </thead>
            <tbody>
              {data?.step_failures.map((s) => (
                <tr key={s.name}>
                  <td>{s.name}</td>
                  <td>{s.failed_attempts}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {data && !data.step_failures.length && (
            <p>No failed step attempts observed.</p>
          )}
          <h3>Jobchain reliability</h3>
          <table>
            <thead>
              <tr>
                <th>Jobchain resource</th>
                <th>Observed runs</th>
                <th>Success</th>
                <th>Failed</th>
              </tr>
            </thead>
            <tbody>
              {data?.jobchain_reliability.map((j) => (
                <tr key={j.job_order_id}>
                  <td>
                    {resources.find((r) => r.job_order_id === j.job_order_id)
                      ?.name || j.job_order_id}
                  </td>
                  <td>{j.observed}</td>
                  <td>{j.success}</td>
                  <td>{j.failed}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      <section className="card table-wrap">
        <h2>Operational history</h2>
        <table>
          <thead>
            <tr>
              <th>Evidence ID</th>
              <th>Observed</th>
              <th>Status / metric</th>
              <th>Value / details</th>
            </tr>
          </thead>
          <tbody>
            {data?.history.map((h) => (
              <tr key={h.id}>
                <td>
                  {domain === "ETL" ? (
                    <button onClick={() => onSelectExecution(h.id)}>
                      {h.provider_execution_id || h.id}
                    </button>
                  ) : (
                    h.id
                  )}
                </td>
                <td>
                  {h.observed_at || h.ended_at || h.started_at || h.created_at}
                </td>
                <td>{h.status || h.metric_name}</td>
                <td>
                  {domain === "VM"
                    ? number(h.value_numeric) + " " + (h.unit || "")
                    : domain === "API"
                      ? "HTTP " +
                        (h.http_status ?? "unknown") +
                        " · " +
                        number(h.response_time_ms) +
                        " ms"
                      : h.sla_status || "Unknown SLA"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && !data.history.length && (
          <p>No historical evidence matches these filters.</p>
        )}
      </section>
      {data && (
        <div className="form-footer">
          <span>{data.total} total records</span>
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
    </div>
  );
}
