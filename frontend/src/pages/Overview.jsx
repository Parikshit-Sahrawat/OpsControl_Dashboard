import KpiCard from "../components/KpiCard";
import StatusBadge from "../components/StatusBadge";
import WorldClock from "../components/WorldClock";

const serviceNowBase = import.meta.env.VITE_SERVICENOW_BASE_URL || "";

function incidentUrl(number) {
  if (!serviceNowBase || !number) return null;
  return `${serviceNowBase.replace(/\/$/, "")}/nav_to.do?uri=incident.do?sysparm_query=number=${encodeURIComponent(number)}`;
}

export default function Overview({ jobs, onSelect, onNavigate }) {
  // Never represent hardcoded examples as operational health.
  // Until these APIs are implemented, show unknown rather than healthy.
  const failed = jobs.filter(job => job.status === "FAILED").length;
  const running = jobs.filter(job => job.status === "RUNNING").length;
  const atRisk = jobs.filter(job => job.status === "LONG_RUNNING").length;
  const kpis = [
    { label: "ETL Jobs", value: String(jobs.length), tone: failed ? "critical-text" : "", detail: `${failed} failed · ${running} running · ${atRisk} at risk`, target: "ETL Jobs" },
    { label: "VM Health", value: "—", tone: "", detail: "Health monitoring not connected", target: "VM Health" },
    { label: "APIs & Services", value: "—", tone: "", detail: "Service monitoring not connected", target: "APIs" },
    { label: "Active Incidents", value: "—", tone: "", detail: "Incident feed not connected", target: "Incidents" },
  ];

  return (
    <>
      <div className="page-heading">
        <div><h1>Overview</h1><p>Production operations — attention first</p></div>
        <div className="overview-header-controls"><span className="refresh">● Auto refresh · 5 seconds</span><WorldClock /></div>
      </div>

      <div className="kpi-grid">
        {kpis.map(kpi => (
          <button key={kpi.label} className="kpi-link" onClick={() => onNavigate?.(kpi.target)} aria-label={`Open ${kpi.label}`}>
            <KpiCard label={kpi.label} value={kpi.value} tone={kpi.tone} detail={kpi.detail} />
          </button>
        ))}
      </div>

      <div className="overview-grid">
        <section className="card">
          <div className="section-heading-row">
            <h2>Recent ETL Jobs</h2>
            <button className="text-link" onClick={() => onNavigate?.("ETL Jobs")}>View all</button>
          </div>
          <table>
            <thead><tr><th>Job</th><th>Server</th><th>Start</th><th>Duration</th><th>Status</th></tr></thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id} onClick={() => onSelect(job)}>
                  <td><b>{job.name}</b><small>{job.environment}</small></td>
                  <td>{job.server}</td><td>{job.start}</td><td>{job.duration}</td>
                  <td><StatusBadge status={job.status}/></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <div className="stack">
          <section className="card">
            <div className="section-heading-row">
              <h2>Recent VM Issues</h2>
              <button className="text-link" onClick={() => onNavigate?.("VM Health")}>View all</button>
            </div>
            <div className="empty-inline">No live VM health feed connected. Add a supported collector to see verified infrastructure status.</div>
          </section>

          <section className="card">
            <div className="section-heading-row">
              <h2>Active Incidents</h2>
              <button className="text-link" onClick={() => onNavigate?.("Incidents")}>View all</button>
            </div>
            <div className="empty-inline">No live incident integration connected. Operational incidents will appear after the alert and incident feed is implemented.</div>
          </section>
        </div>
      </div>
    </>
  );
}
