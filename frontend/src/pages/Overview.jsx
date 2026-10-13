import { hasPermission } from "../permissions";
import { useEffect,useState } from "react";
import { authHeaders } from "../auth";
import KpiCard from "../components/KpiCard";
import StatusBadge from "../components/StatusBadge";
import WorldClock from "../components/WorldClock";
import { useOperationalFeed, scopeQuery } from "../operations";

function MetricIcon({ kind }) {
  const paths = {
    "Data Pipelines": <><rect x="4" y="3" width="7" height="6" rx="1.5" /><rect x="13" y="15" width="7" height="6" rx="1.5" /><path d="M7.5 9v8a1 1 0 0 0 1 1H13M16.5 15V7a1 1 0 0 0-1-1H11" /></>,
    "VM Health": <><rect x="3" y="3" width="18" height="7" rx="2" /><rect x="3" y="14" width="18" height="7" rx="2" /><path d="M7 6.5h.01M7 17.5h.01M11 6.5h6M11 17.5h6" /></>,
    "APIs": <><path d="m8 7-5 5 5 5m8-10 5 5-5 5M14 4l-4 16" /></>,
    "Alerts": <><path d="m12 3 8 4v6c0 4-5 7-8 8-3-1-8-4-8-8V7l8-4Z" /><path d="M12 8v5m0 3h.01" /></>,
  };
  return <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[kind]}</svg>;
}

export default function Overview({ jobs, onSelect, onNavigate, onOpenAlert, organizationIds=[], user }) {
  const summary=useOperationalFeed("/overview?"+scopeQuery(organizationIds));
  const services=useOperationalFeed(hasPermission(user,"resources.view")?"/services?"+scopeQuery(organizationIds):null);
  const alerts=useOperationalFeed(hasPermission(user,"alerts.view")?"/alerts?"+scopeQuery(organizationIds):null);
  const activeAlerts=alerts.data?.summary.OPEN??null;
  const [infrastructure,setInfrastructure]=useState(null);
  useEffect(()=>{
    let active=true;
    const refresh=async()=>{
      try{
        const params=new URLSearchParams();organizationIds.forEach(id=>params.append('organization_id',id));
        const response=await fetch((import.meta.env.VITE_API_BASE_URL||'http://localhost:8000')+'/api/v1/infrastructure/resources?'+params,{headers:authHeaders()});
        if(!response.ok)throw new Error('Infrastructure unavailable');
        const value=await response.json();if(active)setInfrastructure(value);
      }catch{if(active)setInfrastructure(null);}
    };
    if(!hasPermission(user,"resources.view"))return;
    setInfrastructure(null);refresh();const timer=setInterval(refresh,5000);
    return()=>{active=false;clearInterval(timer);};
  },[organizationIds,user?.authorization_revision]);
  const failed = jobs.filter(job => job.status === "FAILED").length;
  const running = jobs.filter(job => job.status === "RUNNING").length;
  const atRisk = jobs.filter(job => job.status === "LONG_RUNNING").length;
  const kpis = [
    { label: "Data Pipelines", value: String(hasPermission(user,"etl.view")?jobs.length:summary.data?.etl_jobs??"—"), tone: failed ? "critical-text" : "", detail: `${failed} failed · ${running} running · ${atRisk} at risk`, target: "Data Pipelines" },
    { label: "VM Health", value: infrastructure?String(infrastructure.total):"—", tone: infrastructure?.summary.CRITICAL?"critical-text":"", detail: infrastructure?`${infrastructure.summary.HEALTHY} healthy · ${infrastructure.summary.CRITICAL+infrastructure.summary.WARNING} need attention · ${infrastructure.summary.UNKNOWN} unknown`:"Infrastructure evidence unavailable", target: "VM Health" },
    { label: "APIs & Services", value: services.data?String(services.data.total):"—", tone: services.data?.summary.CRITICAL?"critical-text":"", detail: services.data?`${services.data.summary.HEALTHY} healthy · ${services.data.summary.CRITICAL} critical · ${services.data.summary.UNKNOWN} unknown`:"Service evidence unavailable", target: "APIs" },
    { label: "Active Alerts", value: activeAlerts!=null?String(activeAlerts):String(summary.data?.active_alerts??"—"), tone: activeAlerts?"critical-text":"", detail: alerts.data?`${alerts.data.summary.OPEN} open · ${alerts.data.summary.RESOLVED} recovered`:"Alert evidence unavailable", target: "Alerts" },
  ];

  return (
    <>
      <div className="page-heading">
        <div><span className="overview-kicker">Operations workspace</span><h1>Overview</h1><p>Production operations — attention first</p></div>
        <div className="overview-header-controls"><span className="refresh">● Auto refresh · 5 seconds</span><WorldClock /></div>
      </div>

      <div className="kpi-grid overview-kpi-grid">
        {kpis.map(kpi => (
          <button key={kpi.label} className={`kpi-link${kpi.target === "Alerts" ? " overview-kpi-featured" : ""}${kpi.target === "Data Pipelines" ? " overview-kpi-wide" : ""}`} disabled={!hasPermission(user,kpi.target==="Data Pipelines"?"etl.view":kpi.target==="Alerts"?"alerts.view":"resources.view")} onClick={() => onNavigate?.(kpi.target)} aria-label={`Open ${kpi.label}`}>
            <KpiCard label={kpi.label} value={kpi.value} tone={kpi.tone} detail={kpi.detail} icon={<MetricIcon kind={kpi.target} />} featured={kpi.target === "Alerts"} />
          </button>
        ))}
      </div>

      <div className="overview-grid">
        <section className="card overview-jobs">
          <div className="section-heading-row">
            <div><span className="overview-kicker">Execution activity</span><h2>Recent Data Pipelines</h2></div>
            <button className="text-link" disabled={!hasPermission(user,"etl.view")} onClick={() => onNavigate?.("Data Pipelines")}>View all</button>
          </div>
          <div className="table-wrap">
          <table>
            <thead><tr><th>Job</th><th>Server</th><th>Start</th><th>Duration</th><th>Status</th></tr></thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id} onClick={() => onSelect(job)}>
                  <td><button type="button" className="entity-link overview-job-link" aria-label={`Inspect ${job.name}`}><b>{job.name}</b></button><small>{job.environment}</small></td>
                  <td className="data-mono">{job.server}</td><td className="data-mono">{job.start}</td><td className="data-mono">{job.duration}</td>
                  <td><StatusBadge status={job.status}/></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        </section>

        <div className="stack overview-companions">
          <section className="card overview-issues">
            <div className="section-heading-row">
              <div><span className="overview-kicker">Infrastructure signals</span><h2>Recent VM Issues</h2></div>
              <button className="text-link" disabled={!hasPermission(user,"resources.view")} onClick={() => onNavigate?.("VM Health")}>View all</button>
            </div>
            {infrastructure?.resources.filter(r=>['WARNING','CRITICAL','UNKNOWN'].includes(r.health)).slice(0,5).map(r=><div className="overview-signal-row" key={r.id}><span className="overview-signal-icon" aria-hidden="true"><MetricIcon kind="VM Health" /></span><div className="overview-signal-copy"><b>{r.name}</b><small><span className="data-mono">{r.open_alert_count}</span> open alerts</small></div><StatusBadge status={r.health} /></div>)}
            {infrastructure&&!infrastructure.resources.some(r=>['WARNING','CRITICAL','UNKNOWN'].includes(r.health))&&<div className="empty-inline overview-empty">No current infrastructure issues in the selected scope.</div>}
            {!infrastructure&&<div className="empty-inline overview-empty">Infrastructure evidence unavailable.</div>}
          </section>

          <section className="card overview-alerts">
            <div className="section-heading-row">
              <div><span className="overview-kicker">Needs attention</span><h2>Active Alerts</h2></div>
              <button className="text-link" onClick={() => onNavigate?.("Alerts")}>View all</button>
            </div>
            {alerts.data?.alerts.filter(row=>row.status!=="RESOLVED").slice(0,5).map(row=><div className="overview-signal-row" key={row.id}><span className="overview-signal-icon" aria-hidden="true"><MetricIcon kind="Alerts" /></span><div className="overview-signal-copy"><button className="text-link" onClick={()=>onOpenAlert(row.id)}>{row.message}</button><small>{row.status} · source {row.status}</small></div></div>)}
            {alerts.data&&!activeAlerts&&<div className="empty-inline overview-empty">No active alerts in the selected organization.</div>}
            {!alerts.data&&<div className="empty-inline overview-empty">Alert evidence unavailable.</div>}
          </section>
        </div>
      </div>
    </>
  );
}
