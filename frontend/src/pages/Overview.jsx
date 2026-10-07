import KpiCard from "../components/KpiCard";
import StatusBadge from "../components/StatusBadge";

export default function Overview({ jobs, onSelect }) {
  return (
    <>
      <div className="page-heading"><div><h1>Overview</h1><p>Production operations — attention first</p></div><span className="refresh">● Auto refresh · 5 seconds</span></div>
      <div className="kpi-grid">
        <KpiCard label="ETL Jobs" value="1" tone="critical-text" detail="failed · 1 running · 1 at risk" />
        <KpiCard label="VM Health" value="1" tone="warning-text" detail="critical issue requiring attention" />
        <KpiCard label="APIs & Services" value="18" tone="healthy-text" detail="healthy · 1 high latency" />
        <KpiCard label="Active Incidents" value="2" tone="critical-text" detail="1 critical · 1 major" />
      </div>
      <div className="overview-grid">
        <section className="card"><h2>Recent ETL Jobs</h2><table><thead><tr><th>Job</th><th>Server</th><th>Start</th><th>Duration</th><th>Status</th></tr></thead><tbody>
          {jobs.map(job => <tr key={job.id} onClick={() => onSelect(job)}><td><b>{job.name}</b><small>{job.environment}</small></td><td>{job.server}</td><td>{job.start}</td><td>{job.duration}</td><td><StatusBadge status={job.status}/></td></tr>)}
        </tbody></table></section>
        <div className="stack"><section className="card"><h2>Recent VM Issues</h2><div className="list-row"><span><b>HERO-PRDAPP001</b><small>D: Drive · 94%</small></span><StatusBadge status="LONG_RUNNING"/></div><div className="list-row"><span><b>ETL-PRD-03</b><small>CPU · 91%</small></span><StatusBadge status="FAILED"/></div></section>
        <section className="card"><h2>Active Incidents</h2><div className="list-row"><span><b>INC0012345</b><small>JC_Pricing_Daily · Database timeout</small></span><StatusBadge status="FAILED"/></div><div className="list-row"><span><b>INC0012339</b><small>Customer_Extract · SLA breach</small></span><StatusBadge status="LONG_RUNNING"/></div></section></div>
      </div>
    </>
  );
}