import { useMemo, useState } from "react";
import StatusBadge from "../components/StatusBadge";

const filters = ["All", "SUCCESS", "FAILED", "RUNNING", "LONG_RUNNING", "NO_RUN"];
const statusLabel = { SUCCESS: "Success", FAILED: "Failed", RUNNING: "Running", LONG_RUNNING: "Long Running", NO_RUN: "No Run" };

export default function ETLJobs({ jobs, onSelect }) {
  const [filter, setFilter] = useState("All");
  const [environment, setEnvironment] = useState("PROD");
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => jobs.filter(job => {
    const matchesFilter = filter === "All" || job.status === filter;
    const matchesEnv = environment === "All" || job.environment === environment;
    const text = `${job.name} ${job.server}`.toLowerCase();
    return matchesFilter && matchesEnv && text.includes(query.toLowerCase());
  }), [jobs, filter, environment, query]);

  return (
    <>
      <div className="page-heading"><div><h1>ETL Jobs</h1><p>Current execution state · PROD monitoring</p></div><span className="refresh">● Auto refresh · 5 seconds</span></div>
      <section className="card filter-card">
        <div className="filter-row">
          <div className="filter-group">{filters.map(item => <button key={item} className={filter === item ? "filter-button active" : "filter-button"} onClick={() => setFilter(item)}>{statusLabel[item] ?? item}</button>)}</div>
          <select value={environment} onChange={e => setEnvironment(e.target.value)}><option>PROD</option><option>All</option></select>
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search job or server..." />
        </div>
      </section>
      <section className="card"><div className="table-heading"><h2>Current Executions</h2><span className="muted small">{filtered.length} jobs</span></div>
        <div className="table-wrap"><table><thead><tr><th>Job Order</th><th>Server</th><th>Start</th><th>End</th><th>Duration</th><th>Expected</th><th>SLA</th><th>Status</th><th>Failed Step</th><th>Incident</th></tr></thead>
        <tbody>{filtered.map(job => <tr key={job.id} onClick={() => onSelect(job)}><td><b>{job.name}</b><small>{job.jobOrderId}</small></td><td>{job.server}</td><td>{job.start}</td><td>{job.end ?? "—"}</td><td>{job.duration}</td><td>{job.expectedRuntime}</td><td>{job.sla}</td><td><StatusBadge status={job.status}/></td><td>{job.failedStep ?? "—"}</td><td>{job.incident ?? "—"}</td></tr>)}</tbody></table></div>
      </section>
      <div className="legend muted small">Click any execution to open the Job Details drawer. Long Running is evaluated against expected runtime; No Run is evaluated against the configured execution window and grace period.</div>
    </>
  );
}