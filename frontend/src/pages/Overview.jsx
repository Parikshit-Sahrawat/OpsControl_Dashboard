import { useEffect,useState } from "react";
import { authHeaders } from "../auth";
import KpiCard from "../components/KpiCard";
import StatusBadge from "../components/StatusBadge";
import WorldClock from "../components/WorldClock";
import { useOperationalFeed, scopeQuery } from "../operations";

export default function Overview({ jobs, onSelect, onNavigate, onOpenIncident, organizationIds=[] }) {
  const services=useOperationalFeed("/services?"+scopeQuery(organizationIds));
  const incidents=useOperationalFeed("/incidents?"+scopeQuery(organizationIds));
  const activeIncidents=incidents.data?Object.entries(incidents.data.summary).filter(([state])=>state!=="RESOLVED").reduce((sum,[,value])=>sum+value,0):null;
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
    setInfrastructure(null);refresh();const timer=setInterval(refresh,5000);
    return()=>{active=false;clearInterval(timer);};
  },[organizationIds]);
  const failed = jobs.filter(job => job.status === "FAILED").length;
  const running = jobs.filter(job => job.status === "RUNNING").length;
  const atRisk = jobs.filter(job => job.status === "LONG_RUNNING").length;
  const kpis = [
    { label: "ETL Jobs", value: String(jobs.length), tone: failed ? "critical-text" : "", detail: `${failed} failed · ${running} running · ${atRisk} at risk`, target: "ETL Jobs" },
    { label: "VM Health", value: infrastructure?String(infrastructure.total):"—", tone: infrastructure?.summary.CRITICAL?"critical-text":"", detail: infrastructure?`${infrastructure.summary.HEALTHY} healthy · ${infrastructure.summary.CRITICAL+infrastructure.summary.WARNING} need attention · ${infrastructure.summary.UNKNOWN} unknown`:"Infrastructure evidence unavailable", target: "VM Health" },
    { label: "APIs & Services", value: services.data?String(services.data.total):"—", tone: services.data?.summary.CRITICAL?"critical-text":"", detail: services.data?`${services.data.summary.HEALTHY} healthy · ${services.data.summary.CRITICAL} critical · ${services.data.summary.UNKNOWN} unknown`:"Service evidence unavailable", target: "APIs" },
    { label: "Active Incidents", value: activeIncidents!=null?String(activeIncidents):"—", tone: activeIncidents?"critical-text":"", detail: incidents.data?`${incidents.data.summary.INVESTIGATING} investigating · ${incidents.data.summary.RESOLVED} closed`:"Incident evidence unavailable", target: "Incidents" },
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
            {infrastructure?.resources.filter(r=>['WARNING','CRITICAL','UNKNOWN'].includes(r.health)).slice(0,5).map(r=><div key={r.id}>{r.name} · {r.health} · {r.open_alert_count} open alerts</div>)}
            {infrastructure&&!infrastructure.resources.some(r=>['WARNING','CRITICAL','UNKNOWN'].includes(r.health))&&<div className="empty-inline">No current infrastructure issues in the selected scope.</div>}
            {!infrastructure&&<div className="empty-inline">Infrastructure evidence unavailable.</div>}
          </section>

          <section className="card">
            <div className="section-heading-row">
              <h2>Active Incidents</h2>
              <button className="text-link" onClick={() => onNavigate?.("Incidents")}>View all</button>
            </div>
            {incidents.data?.incidents.filter(row=>row.status!=="RESOLVED").slice(0,5).map(row=><p key={row.id}><button className="text-link" onClick={()=>onOpenIncident(row.id)}>{row.title}</button><small>{row.status} · source {row.condition_status}</small></p>)}
            {incidents.data&&!activeIncidents&&<div className="empty-inline">No active incidents in the selected organization.</div>}
            {!incidents.data&&<div className="empty-inline">Incident evidence unavailable.</div>}
          </section>
        </div>
      </div>
    </>
  );
}
