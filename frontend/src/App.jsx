import VMHealth from "./pages/VMHealth";
import AccessManagement from "./pages/AccessManagement";
import MonitoringSetup from "./pages/MonitoringSetup";
import APIs from "./pages/APIs";
import Incidents from "./pages/Incidents";
import Reports from "./pages/Reports";
import { useCallback, useEffect, useRef, useState } from "react";
import TopNav from "./components/TopNav";
import JobDetailsDrawer from "./components/JobDetailsDrawer";
import Overview from "./pages/Overview";
import ETLJobs from "./pages/ETLJobs";
import { fetchExecution, fetchExecutionEvidence, fetchExecutions, fetchInvestigation, transitionInvestigation, addInvestigationNote, fetchOrganizations, mapExecution } from "./api";
import ResourceManagement from "./pages/ResourceManagementV2";

function mapDetail(execution, investigation, evidence) {
  const fmt = value => value ? new Date(value).toLocaleTimeString("en-IN",{hour12:false,timeZone:"Asia/Kolkata"}) : "—";
  return {
    job:mapExecution(execution),
    organization:execution.organization, pentahoInstance:"—", detected:fmt(execution.detected_at)+" IST", lastUpdate:fmt(execution.source_evidence?.observed_at)+" IST", logs:evidence?.logs, sourceError:execution.source_error_message, monitoringStatus:execution.monitoring_status, providerExecutionId:execution.provider_execution_id, expectedWindow:[execution.source_evidence?.policy?.expected_window_start,execution.source_evidence?.policy?.expected_window_end].filter(Boolean).join(" – ") ? [execution.source_evidence?.policy?.expected_window_start,execution.source_evidence?.policy?.expected_window_end].join(" – ")+" ("+(execution.source_evidence?.policy?.timezone || "UTC")+")" : execution.source_evidence?.deadline ? fmt(execution.source_evidence.deadline)+" IST" : undefined, gracePeriod:execution.source_evidence?.policy?.grace_seconds!=null ? execution.source_evidence.policy.grace_seconds+"s" : undefined,
    slaStatus:execution.sla_status || "—", failureCategory:investigation?.failure_category, suspectedCause:investigation?.suspected_cause, confidence:investigation?.confidence,
    steps:(execution.steps||[]).map(s=>({name:s.name,status:s.status,type:s.step_type,duration:s.duration_seconds!=null?Math.floor(s.duration_seconds/60)+"m "+String(s.duration_seconds%60).padStart(2,"0")+"s":null})),
    timeline:(evidence?.timeline||[]).map(item=>({...item,time:fmt(item.time)+" IST"})),
    incidentHistory:(evidence?.alert_events||[]).map(item=>({time:fmt(item.timestamp)+" IST",event:item.event_type,reference:item.reference})),
    recentHistory:(evidence?.history||[]).filter(item=>item.id!==execution.id).map(item=>({id:item.id,time:fmt(item.detected_at)+" IST",status:item.status,reason:item.provider_execution_id})),
    investigation:investigation?{
      status:investigation.status,operator:investigation.operator||"—",started:investigation.started_at?fmt(investigation.started_at)+" IST":"—",
      notes:(investigation.notes||[]).map(n=>({timestamp:fmt(n.timestamp),operator:n.operator,text:n.text})),
      transitions:(investigation.transitions||[]).map(t=>({previous:t.previous_status,next:t.new_status,timestamp:fmt(t.timestamp)+" IST",operator:t.operator}))
    }:undefined
  };
}

export default function App({ user }) {
  const [active,setActive]=useState("Overview"),[jobs,setJobs]=useState([]),[details,setDetails]=useState({}),[selectedId,setSelectedId]=useState(null),[loading,setLoading]=useState(true),[error,setError]=useState(null);
  const [organizations,setOrganizations]=useState([]);
  const [scopeReady,setScopeReady]=useState(false),[target,setTarget]=useState({});
  const generation=useRef(0);
  const [organizationIds,setOrganizationIds]=useState(()=>{try{return JSON.parse(window.localStorage.getItem("opscontrol.organizationIds") || "[]");}catch{return [];}});
  const selected=jobs.find(job=>job.id===selectedId)||details[selectedId]?.job||null;
  const refresh=useCallback(async()=>{if(!scopeReady)return;const version=generation.current;try{const value=await fetchExecutions({latest_only:true,organization_ids:organizationIds});if(version===generation.current){setError(null);setJobs(value);}}catch(e){if(version===generation.current)setError(e.message||"Unable to load ETL executions");}finally{if(version===generation.current)setLoading(false);}},[organizationIds,scopeReady]);
  useEffect(()=>{fetchOrganizations().then(orgs=>{setOrganizations(orgs);
    const saved = (()=>{try{return JSON.parse(window.localStorage.getItem("opscontrol.organizationIds") || "[]");}catch{return [];}})();
    const valid = saved.filter(id => orgs.some(o => o.id === id));
    const selected = valid.length ? valid : orgs.map(o => o.id);
    setOrganizationIds(selected);
    setScopeReady(true);
    window.localStorage.setItem("opscontrol.organizationIds", JSON.stringify(selected));
  }).catch(e=>setError(e.message||"Unable to load organizations"));},[]);
  useEffect(()=>{window.localStorage.setItem("opscontrol.organizationIds",JSON.stringify(organizationIds));},[organizationIds]);
  const organizationId = organizationIds[0] || "";
  useEffect(()=>{generation.current++;refresh();const timer=window.setInterval(refresh,5000);return()=>{generation.current++;window.clearInterval(timer);};},[refresh]);
  const selectJob=async job=>{const id=typeof job==="string"?job:job.id,version=generation.current;setSelectedId(id);try{const execution=await fetchExecution(id);const evidence=await fetchExecutionEvidence(id);let investigation=null;try{investigation=await fetchInvestigation(id);}catch(e){if(e.message!=="Investigation not found")throw e;}if(version===generation.current)setDetails(current=>({...current,[id]:mapDetail(execution,investigation,evidence)}));}catch(e){if(version===generation.current)setError(e.message||"Unable to load execution details");}};
  useEffect(()=>{if(selectedId)selectJob(selectedId);},[jobs,selectedId]);
  const updateInvestigation=async(jobId,next)=>{try{await transitionInvestigation(jobId,next);await selectJob(jobId);}catch(e){setError(e.message||"Unable to update investigation");}};
  const addNote=async(jobId,text)=>{try{await addInvestigationNote(jobId,text);await selectJob(jobId);}catch(e){setError(e.message||"Unable to add note");}};
  const navigate=page=>{setTarget({});setActive(page);setSelectedId(null);};
  const openSource=(id,type)=>{setSelectedId(null);setTarget({sourceId:id});setActive(["API","HTTP","HTTPS"].includes(type)?"APIs":"VM Health");};
  const openIncident=id=>{setSelectedId(null);setTarget({incidentId:id});setActive("Incidents");};
  const scopeKey=organizationIds.join(",");
  return <div className="app-shell"><TopNav active={active} onChange={navigate} organizations={organizations} organizationIds={organizationIds} onOrganizationChange={ids=>{generation.current++;setSelectedId(null);setDetails({});setJobs([]);setLoading(true);setTarget({});setOrganizationIds(ids)}} platformAdmin={user?.platform_admin}/><main className="content">
    {!scopeReady&&<p>{error||"Loading authorized organizations…"}</p>}
    {scopeReady&&error&&active!=="ETL Jobs"&&<p role="alert">{error}</p>}
    {scopeReady&&active==="Overview"&&<Overview key={scopeKey} organizationIds={organizationIds} jobs={jobs} onSelect={selectJob} onNavigate={navigate} onOpenIncident={openIncident}/>}
    {active==="ETL Jobs"&&<ETLJobs jobs={jobs} loading={loading} error={error} onRetry={()=>{setLoading(true);refresh()}} onSelect={selectJob}/>}
    {active==="Access Management"&&user?.platform_admin&&<AccessManagement />}
    {scopeReady&&active==="Resource Management"&&<ResourceManagement key={scopeKey} organizationId={organizationId} organizationIds={organizationIds}/>}
    {scopeReady&&active==="VM Health"&&<VMHealth key={scopeKey+target.sourceId} organizationIds={organizationIds} initialSourceId={target.sourceId}/> }
    {scopeReady&&active==="Monitoring Setup"&&<MonitoringSetup key={scopeKey} organizationId={organizationId} organizationName={organizations.find(org=>org.id===organizationId)?.name} user={user}/> }
    {scopeReady&&active==="APIs"&&<APIs key={scopeKey+target.sourceId} organizationIds={organizationIds} initialSourceId={target.sourceId} onNavigate={navigate}/>}
    {scopeReady&&active==="Incidents"&&<Incidents key={scopeKey+target.incidentId} organizationIds={organizationIds} user={user} initialIncidentId={target.incidentId} onSelectExecution={selectJob} onOpenSource={openSource}/>}
    {scopeReady&&active==="Reports"&&<Reports key={scopeKey} organizationIds={organizationIds} onSelectExecution={selectJob} onOpenSource={openSource} onOpenIncident={openIncident}/>}
  </main><JobDetailsDrawer job={selected} details={selected?details[selected.id]:null} onClose={()=>setSelectedId(null)} onInvestigationChange={updateInvestigation} onAddNote={addNote} onSelectExecution={selectJob} canInvestigate={!!(user?.platform_admin || user?.memberships?.some(m=>m.organization_id===selected?.organizationId && ["operator","org_admin"].includes(m.role)))}/></div>;
}
