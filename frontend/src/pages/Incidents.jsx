import { useEffect,useState } from "react";
import { operations,useOperationalFeed,scopeQuery,evidenceTime } from "../operations";
import EvidenceDrawer from "../components/EvidenceDrawer";
import InventoryPager from "../components/InventoryPager";
import StatusBadge from "../components/StatusBadge";
export default function Incidents({organizationIds,user,initialIncidentId,onSelectExecution,onOpenSource}) {
  const [status,setStatus]=useState("ALL"),[source,setSource]=useState("ALL"),[search,setSearch]=useState("");
  const [offset,setOffset]=useState(0),scope=organizationIds.join(",");
  useEffect(()=>setOffset(0),[scope,status,source,search]);
  const {data,error,refresh}=useOperationalFeed("/incidents?"+scopeQuery(organizationIds,{status,source_kind:source,search,offset}));
  const [id,setId]=useState(initialIncidentId||null),[detail,setDetail]=useState(null),[actionError,setActionError]=useState(""),[text,setText]=useState(""),[busy,setBusy]=useState(false),[revision,setRevision]=useState(0);
  useEffect(()=>{setId(initialIncidentId||null);},[initialIncidentId]);
  useEffect(()=>{setText("");},[id]);
  useEffect(()=>{let live=true;setDetail(null);setActionError("");if(id)operations("/incidents/"+id).then(value=>{if(live)setDetail(value);}).catch(e=>{if(live)setActionError(e.message);});return()=>{live=false;};},[id,revision]);
  // Preserve an operator's draft while refreshing source recovery and activity.
  useEffect(()=>{let live=true;if(id&&data)operations("/incidents/"+id).then(value=>{if(live)setDetail(value);}).catch(e=>{if(live)setActionError(e.message);});return()=>{live=false;};},[id,data]);
  const canWrite=detail&&!!(user?.platform_admin||user?.memberships?.some(m=>m.organization_id===detail.organization_id&&["operator","org_admin"].includes(m.role)));
  const act=async(path,body)=>{if(busy)return;setBusy(true);setActionError("");try{const value=await operations("/incidents/"+id+path,{method:"POST",body:JSON.stringify(body)});setDetail(value);if(path==="/notes")setText("");refresh();}catch(e){setActionError(e.message);}finally{setBusy(false);}};
  const transitions=detail?.status==="OPEN"?["ACKNOWLEDGED"]:detail?.status==="ACKNOWLEDGED"?["INVESTIGATING",...(detail.condition_status==="RECOVERED"?["RESOLVED"]:[])]:detail?.status==="INVESTIGATING"&&detail.condition_status==="RECOVERED"?["RESOLVED"]:[];
  return <div className="operations-page"><div className="page-heading"><div><h1>Incidents</h1><p>Local alert episodes · source recovery and operator closure tracked separately</p></div><button onClick={()=>{refresh();setRevision(v=>v+1);}}>Refresh incidents</button></div>{error&&<p role="alert">{error}</p>}
    <div className="kpi-grid">{["OPEN","ACKNOWLEDGED","INVESTIGATING","RESOLVED"].map(state=><button key={state} className="card operational-kpi" aria-pressed={status===state} onClick={()=>setStatus(state)}><b>{state}</b><p>{data?.summary[state]??"—"}</p></button>)}</div>
    <section className="card"><div className="operational-filters"><label>Search incidents<input value={search} onChange={e=>setSearch(e.target.value)}/></label><label>Incident status<select value={status} onChange={e=>setStatus(e.target.value)}>{["ALL","OPEN","ACKNOWLEDGED","INVESTIGATING","RESOLVED"].map(state=><option key={state}>{state}</option>)}</select></label><label>Incident source<select value={source} onChange={e=>setSource(e.target.value)}>{["ALL","METRIC","ETL"].map(state=><option key={state}>{state}</option>)}</select></label></div>
      {!data&&!error&&<p>Loading incidents…</p>}
      <table><thead><tr><th>Incident</th><th>Source</th><th>Severity</th><th>Operator status</th><th>Source condition</th><th>Opened</th></tr></thead><tbody>{data?.incidents.map(row=><tr key={row.id} data-testid="incident-row"><td><button className="text-link" onClick={()=>setId(row.id)}>{row.title}</button><small>{row.id.slice(0,8)}</small></td><td>{row.source_kind}</td><td><StatusBadge status={row.severity}/></td><td><StatusBadge status={row.status}/></td><td><StatusBadge status={row.condition_status}/></td><td>{evidenceTime(row.opened_at)}</td></tr>)}</tbody></table>{data&&!data.incidents.length&&<p>No incidents match this organization and filters.</p>}
      <InventoryPager data={data} onOffsetChange={setOffset}/>
    </section>
    {id&&<EvidenceDrawer title={detail?.title||"Incident investigation"} onClose={()=>setId(null)}>{actionError&&<p role="alert">{actionError}</p>}{detail&&<><p><b>{detail.status}</b> · {detail.severity} · Source {detail.condition_status}</p><p>Opened {evidenceTime(detail.opened_at)}<br/>Source recovered {evidenceTime(detail.recovered_at)}<br/>Operator resolved {evidenceTime(detail.resolved_at)}</p>
      <div className="operational-actions">{detail.history_id&&<button onClick={()=>{setId(null);onSelectExecution(detail.history_id);}}>Investigate ETL execution</button>}{detail.data_source_id&&<button onClick={()=>{setId(null);onOpenSource(detail.data_source_id,detail.source_type);}}>Open resource evidence</button>}{canWrite&&transitions.map(state=><button disabled={busy} key={state} onClick={()=>act("/transitions",{new_status:state})}>Mark {state}</button>)}</div>
      {canWrite&&detail.condition_status==="ACTIVE"&&detail.status!=="RESOLVED"&&<p>Resolution becomes available after source recovery.</p>}
      {canWrite&&<form className="incident-note" onSubmit={e=>{e.preventDefault();act("/notes",{text});}}><label>Investigation note<textarea value={text} disabled={busy} maxLength={2000} onChange={e=>setText(e.target.value)} placeholder="Add incident evidence or operator observation"/></label><button disabled={busy||!text.trim()}>Save incident note</button></form>}
      <h3>Investigation and alert history</h3>{detail.activity.map(e=><div key={e.id} className="evidence-event"><b>{e.event_type}{e.new_status?" · "+e.new_status:""}</b><small>{evidenceTime(e.occurred_at)} · {e.actor}</small>{e.text&&<p>{e.text}</p>}</div>)}</>}</EvidenceDrawer>}
  </div>;
}
