import { useCallback, useEffect, useState } from "react";
import TopNav from "./components/TopNav";
import JobDetailsDrawer from "./components/JobDetailsDrawer";
import Overview from "./pages/Overview";
import ETLJobs from "./pages/ETLJobs";
import { fetchExecution, fetchExecutions, fetchInvestigation, transitionInvestigation, addInvestigationNote } from "./api";

function mapDetail(execution, investigation) {
  const fmt = value => value ? new Date(value).toLocaleTimeString("en-IN",{hour12:false}) : "—";
  return {
    organization:execution.organization, pentahoInstance:"—", detected:fmt(execution.detected_at)+" IST", lastUpdate:fmt(execution.ended_at)+" IST",
    slaStatus:execution.sla_status || "—", failureCategory:investigation?.failure_category, suspectedCause:investigation?.suspected_cause, confidence:investigation?.confidence,
    steps:(execution.steps||[]).map(s=>({name:s.name,status:s.status,type:s.step_type,duration:s.duration_seconds!=null?Math.floor(s.duration_seconds/60)+"m "+String(s.duration_seconds%60).padStart(2,"0")+"s":null})),
    timeline:[
      execution.started_at&&{time:fmt(execution.started_at),event:"Job started",source:"Pentaho"},
      execution.detected_at&&{time:fmt(execution.detected_at),event:"Execution detected",source:"OpsControl"},
      execution.ended_at&&{time:fmt(execution.ended_at),event:"Job "+execution.status.toLowerCase(),source:"Pentaho"}
    ].filter(Boolean),
    incidentHistory:execution.incident_number?[{time:"—",event:"Incident reference",reference:execution.incident_number}]:[],
    recentHistory:[],
    investigation:investigation?{
      status:investigation.status,operator:investigation.operator||"—",started:investigation.started_at?fmt(investigation.started_at)+" IST":"—",
      notes:(investigation.notes||[]).map(n=>({timestamp:fmt(n.timestamp),operator:n.operator,text:n.text})),
      transitions:(investigation.transitions||[]).map(t=>({previous:t.previous_status,next:t.new_status,timestamp:fmt(t.timestamp)+" IST",operator:t.operator}))
    }:undefined
  };
}

export default function App() {
  const [active,setActive]=useState("Overview"),[jobs,setJobs]=useState([]),[details,setDetails]=useState({}),[selectedId,setSelectedId]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(null);
  const selected=jobs.find(job=>job.id===selectedId)||null;
  const refresh=useCallback(async()=>{try{setError(null);setJobs(await fetchExecutions({environment:"PROD"}));}catch(e){setError(e.message||"Unable to load ETL executions");}finally{setLoading(false);}},[]);
  useEffect(()=>{refresh();const timer=window.setInterval(refresh,5000);return()=>window.clearInterval(timer);},[refresh]);
  const selectJob=async job=>{const id=typeof job==="string"?job:job.id;setSelectedId(id);try{const execution=await fetchExecution(id);let investigation=null;try{investigation=await fetchInvestigation(id);}catch{}setDetails(current=>({...current,[id]:mapDetail(execution,investigation)}));}catch(e){setError(e.message||"Unable to load execution details");}};
  const updateInvestigation=async(jobId,next)=>{try{await transitionInvestigation(jobId,next);await selectJob(jobId);}catch(e){setError(e.message||"Unable to update investigation");}};
  const addNote=async(jobId,text)=>{try{await addInvestigationNote(jobId,text);await selectJob(jobId);}catch(e){setError(e.message||"Unable to add note");}};
  return <div className="app-shell"><TopNav active={active} onChange={page=>{setActive(page);setSelectedId(null)}}/><main className="content">
    {active==="Overview"&&<Overview jobs={jobs} onSelect={selectJob}/>}
    {active==="ETL Jobs"&&<ETLJobs jobs={jobs} loading={loading} error={error} onRetry={()=>{setLoading(true);refresh()}} onSelect={selectJob}/>}
    {![ "Overview","ETL Jobs" ].includes(active)&&<div className="card placeholder"><h1>{active}</h1><p>Page structure reserved for the next implementation stage.</p></div>}
  </main><JobDetailsDrawer job={selected} details={selected?details[selected.id]:null} onClose={()=>setSelectedId(null)} onInvestigationChange={updateInvestigation} onAddNote={addNote}/></div>;
}
