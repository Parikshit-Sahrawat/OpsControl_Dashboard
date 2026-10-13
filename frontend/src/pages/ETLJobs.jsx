import { useMemo, useState } from "react";
import StatusBadge from "../components/StatusBadge";

const filters = [
  "All",
  "SUCCESS",
  "FAILED",
  "RUNNING",
  "LONG_RUNNING",
  "NO_RUN",
];
const statusLabel = {
  SUCCESS: "Success",
  FAILED: "Failed",
  RUNNING: "Running",
  LONG_RUNNING: "Long Running",
  NO_RUN: "No Run",
};
const executionTypes = ["All", "SCHEDULED", "MANUAL"];

export default function ETLJobs({
  jobs = [],
  loading = false,
  error = null,
  onRetry,
  onSelect,
  embedded = false,
}) {
  const [filter, setFilter] = useState("All"),
    [environment, setEnvironment] = useState("All"),
    [executionType, setExecutionType] = useState("All"),
    [query, setQuery] = useState("");
  const environments = useMemo(
    () => [
      "All",
      ...Array.from(
        new Set(jobs.map((j) => j.environment).filter(Boolean)),
      ).sort(),
    ],
    [jobs],
  );
  const filtered = useMemo(
    () =>
      jobs.filter((job) => {
        const a = filter === "All" || job.status === filter,
          b = environment === "All" || job.environment === environment,
          c = executionType === "All" || job.executionType === executionType,
          t = `${job.name} ${job.server} ${job.jobOrderId}`.toLowerCase();
        return a && b && c && t.includes(query.toLowerCase());
      }),
    [jobs, filter, environment, executionType, query],
  );
  const counts = useMemo(
    () =>
      filters.reduce(
        (a, k) => (
          (a[k] =
            k === "All"
              ? jobs.length
              : jobs.filter((j) => j.status === k).length),
          a
        ),
        {},
      ),
    [jobs],
  );
  return (
    <>
      <div className="page-heading">
        <div>
          {embedded ? (
            <h2>Execution investigation</h2>
          ) : (
            <h1>ETL Monitoring</h1>
          )}
          <p>Current execution state · operational monitoring</p>
        </div>
        <span className="refresh">● Auto refresh · 5 seconds</span>
      </div>
      <section className="card filter-card">
        <div className="filter-row">
          <div className="filter-group">
            {filters.map((item) => (
              <button
                key={item}
                className={
                  filter === item ? "filter-button active" : "filter-button"
                }
                onClick={() => setFilter(item)}
              >
                {statusLabel[item] ?? item}
                <span className="filter-count">{counts[item] ?? 0}</span>
              </button>
            ))}
          </div>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
          >
            {environments.map((env) => (
              <option key={env}>{env}</option>
            ))}
          </select>
          <select
            value={executionType}
            onChange={(e) => setExecutionType(e.target.value)}
          >
            {executionTypes.map((type) => (
              <option key={type}>{type}</option>
            ))}
          </select>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search job, ID or server..."
          />
        </div>
      </section>
      <section className="card">
        <div className="table-heading">
          <div>
            <h2>Current Executions</h2>
            <span className="muted small">
              {filtered.length} matching executions
            </span>
          </div>
          <span className="muted small">
            Expected runtime → early warning · SLA → breach
          </span>
        </div>
        {loading ? (
          <div className="state-panel">
            <div className="spinner" />
            <h3>Loading pipeline executions</h3>
            <p>Refreshing current execution state…</p>
          </div>
        ) : error ? (
          <div className="state-panel error-state">
            <h3>Unable to load pipeline executions</h3>
            <p>{error}</p>
            <button className="primary-button" onClick={onRetry}>
              Retry
            </button>
          </div>
        ) : filtered.length === 0 ? (
          <div className="state-panel">
            <h3>No executions found</h3>
            <p>
              Try another status, environment, execution type, or search term.
            </p>
            <button
              className="filter-button"
              onClick={() => {
                setFilter("All");
                setEnvironment("PROD");
                setExecutionType("All");
                setQuery("");
              }}
            >
              Clear filters
            </button>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job Order</th>
                  <th>Server</th>
                  <th>Execution</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Duration</th>
                  <th>Expected / SLA</th>
                  <th>Status</th>
                  <th>Monitor</th>
                  <th>Failed Step</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((job) => {
                  const runtime =
                    job.slaStatus === "BREACHED"
                      ? "SLA_BREACH"
                      : job.status === "LONG_RUNNING"
                        ? "AT_RISK"
                        : job.status;
                  return (
                    <tr key={job.id} onClick={() => onSelect(job.id)}>
                      <td>
                        <b>{job.name}</b>
                        <small>
                          {job.jobOrderId} · {job.id}
                        </small>
                      </td>
                      <td>
                        {job.server}
                        <small>{job.environment}</small>
                      </td>
                      <td>
                        <span className="execution-type">
                          {job.executionType}
                        </span>
                      </td>
                      <td>{job.start ?? "—"}</td>
                      <td>{job.end ?? "—"}</td>
                      <td>
                        <b>{job.duration ?? "—"}</b>
                      </td>
                      <td>
                        <span>
                          {job.expectedRuntime ?? "—"} / {job.sla ?? "—"}
                        </span>
                        {["AT_RISK", "SLA_BREACH"].includes(runtime) && (
                          <small
                            className={
                              runtime === "SLA_BREACH"
                                ? "critical-text"
                                : "warning-text"
                            }
                          >
                            {runtime === "SLA_BREACH"
                              ? "SLA breach"
                              : "Expected runtime exceeded"}
                          </small>
                        )}
                      </td>
                      <td>
                        <StatusBadge status={job.status} />
                      </td>
                      <td>{job.monitoringStatus || "UNKNOWN"}</td>
                      <td>{job.failedStep ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <div className="legend muted small">
        <b>Monitoring logic:</b> No Run is raised only after the configured
        expected execution window plus grace period. Long Running starts after
        expected runtime; SLA breach is reached at the SLA threshold. OpsControl
        does not execute or restart production jobs.
      </div>
    </>
  );
}
