import { useMemo, useState } from "react";
import StatusBadge from "../components/StatusBadge";

const filters = ["All", "SUCCESS", "FAILED", "RUNNING", "LONG_RUNNING", "NO_RUN"];
const statusLabel = { SUCCESS: "Success", FAILED: "Failed", RUNNING: "Running", LONG_RUNNING: "Long Running", NO_RUN: "No Run" };
const executionTypes = ["All", "SCHEDULED", "MANUAL"];

function parseMinutes(value) {
  if (!value) return 0;
  const m = String(value).match(/(?:(\d+)h\s*)?(?:(\d+)m\s*)?(?:(\d+)s)?/);
  if (!m) return 0;
  return Number(m[1] || 0) * 60 + Number(m[2] || 0) + Number(m[3] || 0) / 60;
}

function runtimeState(job) {
  if (!["RUNNING", "LONG_RUNNING"].includes(job.status)) return job.status;
  const runtime = parseMinutes(job.duration);
  const expected = parseMinutes(job.expectedRuntime);
  const sla = parseMinutes(job.sla);
  if (runtime >= sla) return "SLA_BREACH";
  if (runtime >= expected) return "AT_RISK";
  return "ON_TRACK";
}

export default function ETLJobs({ jobs = [], loading = false, error = null, onRetry, onSelect }) {
  const [filter, setFilter] = useState("All");
  const [environment, setEnvironment] = useState("PROD");
  const [executionType, setExecutionType] = useState("All");
  const [query, setQuery] = useState("");

  const environments = useMemo(() => ["All", ...Array.from(new Set(jobs.map(j => j.environment).filter(Boolean))).sort()], [jobs]);

  const filtered = useMemo(() => jobs.filter(job => {
    const matchesFilter = filter === "All" || job.status === filter;
    const matchesEnv = environment === "All" || job.environment === environment;
    const matchesType = executionType === "All" || job.executionType === executionType;
    const text = `${job.name} ${job.server} ${job.jobOrderId}`.toLowerCase();
    return matchesFilter && matchesEnv && matchesType && text.includes(query.toLowerCase());
  }), [jobs, filter, environment, executionType, query]);

  const counts = useMemo(() => filters.reduce((acc, key) => {
    acc[key] = key === "All" ? jobs.length : jobs.filter(j => j.status === key).length;
    return acc;
  }, {}), [jobs]);

  return (
    <>
      <div className="page-heading">
        <div><h1>ETL Jobs</h1><p>Current execution state · operational monitoring</p></div>
        <span className="refresh">● Auto refresh · 5 seconds</span>
      </div>

      <section className="card filter-card">
        <div className="filter-row">
          <div className="filter-group">
            {filters.map(item => (
              <button key={item} className={filter === item ? "filter-button active" : "filter-button"} onClick={() => setFilter(item)}>
                {statusLabel[item] ?? item}<span className="filter-count">{counts[item] ?? 0}</span>
              </button>
            ))}
          </div>
          <select value={environment} onChange={e => setEnvironment(e.target.value)} aria-label="Environment">
            {environments.map(env => <option key={env}>{env}</option>)}
          </select>
          <select value={executionType} onChange={e => setExecutionType(e.target.value)} aria-label="Execution type">
            {executionTypes.map(type => <option key={type}>{type}</option>)}
          </select>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search job, ID or server..." />
        </div>
        {environment !== "PROD" && environment !== "All" && (
          <div className="scope-banner">Non-PROD environment selected. Regular automated monitoring is currently scoped to PROD; this view is available for configuration/validation only.</div>
        )}
      </section>

      <section className="card">
        <div className="table-heading">
          <div><h2>Current Executions</h2><span className="muted small">{filtered.length} matching executions</span></div>
          <span className="muted small">Expected runtime → early warning · SLA → breach</span>
        </div>

        {loading ? (
          <div className="state-panel"><div className="spinner" /><h3>Loading ETL executions</h3><p>Refreshing current execution state…</p></div>
        ) : error ? (
          <div className="state-panel error-state"><h3>Unable to load ETL executions</h3><p>{error}</p><button className="primary-button" onClick={onRetry}>Retry</button></div>
        ) : filtered.length === 0 ? (
          <div className="state-panel"><h3>No executions found</h3><p>Try another status, environment, execution type, or search term.</p><button className="filter-button" onClick={() => { setFilter("All"); setEnvironment("PROD"); setExecutionType("All"); setQuery(""); }}>Clear filters</button></div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead><tr><th>Job Order</th><th>Server</th><th>Execution</th><th>Start</th><th>End</th><th>Duration</th><th>Expected / SLA</th><th>Status</th><th>Failed Step</th><th>Incident</th></tr></thead>
              <tbody>
                {filtered.map(job => {
                  const runtime = runtimeState(job);
                  return (
                    <tr key={job.id} onClick={() => onSelect(job)}>
                      <td><b>{job.name}</b><small>{job.jobOrderId} · {job.id}</small></td>
                      <td>{job.server}<small>{job.environment}</small></td>
                      <td><span className="execution-type">{job.executionType}</span></td>
                      <td>{job.start ?? "—"}</td>
                      <td>{job.end ?? "—"}</td>
                      <td><b>{job.duration ?? "—"}</b></td>
                      <td>
                        <span>{job.expectedRuntime ?? "—"} / {job.sla ?? "—"}</span>
                        {["AT_RISK", "SLA_BREACH"].includes(runtime) && <small className={runtime === "SLA_BREACH" ? "critical-text" : "warning-text"}>{runtime === "SLA_BREACH" ? "SLA breach" : "Expected runtime exceeded"}</small>}
                      </td>
                      <td><StatusBadge status={job.status}/></td>
                      <td>{job.failedStep ?? "—"}</td>
                      <td>{job.incident ?? "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <div className="legend muted small">
        <b>Monitoring logic:</b> No Run is raised only after the configured expected execution window plus grace period. Long Running starts after expected runtime; SLA Breach is reached at the SLA threshold. OpsControl does not execute or restart production jobs.
      </div>
    </>
  );
}