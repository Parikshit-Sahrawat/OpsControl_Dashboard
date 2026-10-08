import KpiCard from "../components/KpiCard";
import StatusBadge from "../components/StatusBadge";

const serviceNowBase = import.meta.env.VITE_SERVICENOW_BASE_URL || "";

function incidentUrl(number) {
  if (!serviceNowBase || !number) return null;
  return `${serviceNowBase.replace(/\/$/, "")}/nav_to.do?uri=incident.do?sysparm_query=number=${encodeURIComponent(number)}`;
}

export default function Overview({ jobs, onSelect, onNavigate }) {
  const vmIssues = [
    { hostname: "HERO-PRDAPP001", metric: "D: Drive", value: "94%", condition: "Low Disk Space", status: "CRITICAL" },
    { hostname: "ETL-PRD-03", metric: "CPU", value: "91%", condition: "High Utilization", status: "WARNING" },
  ];

  const incidents = [
    { number: "INC0012345", summary: "JC_Pricing_Daily · Database timeout", severity: "CRITICAL" },
    { number: "INC0012339", summary: "Customer_Extract · SLA breach", severity: "WARNING" },
  ];

  return (
    <>
      <div className="page-heading">
        <div><h1>Overview</h1><p>Production operations — attention first</p></div>
        <span className="refresh">● Auto refresh · 5 seconds</span>
      </div>

      <div className="kpi-grid">
        <KpiCard label="ETL Jobs" value="1" tone="critical-text" detail="failed · 1 running · 1 at risk" />
        <KpiCard label="VM Health" value="1" tone="warning-text" detail="critical issue requiring attention" />
        <KpiCard label="APIs & Services" value="18" tone="healthy-text" detail="healthy · 1 high latency" />
        <KpiCard label="Active Incidents" value="2" tone="critical-text" detail="1 critical · 1 major" />
      </div>

      <div className="overview-grid">
        <section className="card">
          <h2>Recent ETL Jobs</h2>
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
            {vmIssues.map(issue => (
              <div className="list-row vm-issue-row" key={issue.hostname + issue.metric}>
                <button className="entity-link" onClick={() => onNavigate?.("VM Health")}>
                  <b>{issue.hostname}</b>
                  <small>{issue.metric} · {issue.value}</small>
                </button>
                <div className="vm-issue-meta">
                  <span className="issue-condition">{issue.condition}</span>
                  <StatusBadge status={issue.status}/>
                </div>
              </div>
            ))}
          </section>

          <section className="card">
            <div className="section-heading-row">
              <h2>Active Incidents</h2>
              <button className="text-link" onClick={() => onNavigate?.("Incidents")}>View all</button>
            </div>
            {incidents.map(incident => {
              const url = incidentUrl(incident.number);
              return (
                <div className="list-row" key={incident.number}>
                  {url ? (
                    <a className="entity-link incident-link" href={url} target="_blank" rel="noreferrer">
                      <b>{incident.number}</b><small>{incident.summary}</small>
                    </a>
                  ) : (
                    <button className="entity-link incident-link" onClick={() => onNavigate?.("Incidents")}>
                      <b>{incident.number}</b><small>{incident.summary}</small>
                    </button>
                  )}
                  <StatusBadge status={incident.severity}/>
                </div>
              );
            })}
            {!serviceNowBase && <div className="source-fact">ServiceNow URL is not configured. Set <code>VITE_SERVICENOW_BASE_URL</code> to make incident numbers open the corresponding ServiceNow record.</div>}
          </section>
        </div>
      </div>
    </>
  );
}
