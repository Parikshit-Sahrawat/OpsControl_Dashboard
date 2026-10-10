import { useCallback, useEffect, useState } from "react";
import { authHeaders } from "../auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
async function api(path, options={}) {
  const response=await fetch(BASE+path,{...options,
    headers:{"Content-Type":"application/json",...authHeaders(),...(options.headers||{})}});
  if(!response.ok) {
    const err=await response.json().catch(()=>({}));
    const detail=err.detail;
    throw new Error(typeof detail==="string"?detail:JSON.stringify(detail||"Request failed"));
  }
  return response.status===204?null:response.json();
}
const API="/api/v1";
const kinds=["METRIC","LOG","ALERT"];
const DEFAULTS={
  METRIC:{name:"probe_up",metric_type:"GAUGE"},
  LOG:{name:"http_probe_events",source_type:"HTTP",parser_type:"RAW"},
  ALERT:{name:"availability_down",metric_name:"probe_up",operator:"LT",threshold_value:0.5,consecutive_breaches:1}
};

export default function MonitoringSetup({organizationId,user}) {
  const [sources,setSources]=useState([]),[catalogs,setCatalogs]=useState([]),[workers,setWorkers]=useState([]);
  const [sourceId,setSourceId]=useState(""),[workerId,setWorkerId]=useState("");
  const [selectedRules,setSelectedRules]=useState([]),[includeTemplates,setIncludeTemplates]=useState(false);
  const [kind,setKind]=useState("METRIC"),[ruleName,setRuleName]=useState("readiness");
  const [definition,setDefinition]=useState(JSON.stringify(DEFAULTS.METRIC,null,2));
  const [preview,setPreview]=useState(null),[activation,setActivation]=useState(null);
  const [diagnostics,setDiagnostics]=useState(null),[diagBusy,setDiagBusy]=useState(false);
  const [editRule,setEditRule]=useState(""),[editDefinition,setEditDefinition]=useState("");
  const [error,setError]=useState(""),[message,setMessage]=useState(""),[busy,setBusy]=useState(false);
  const [enrollName,setEnrollName]=useState("demo-runner"),[enrollHost,setEnrollHost]=useState("portal.example.test");
  const [enrollCIDR,setEnrollCIDR]=useState("10.20.0.0/16"),[oneTimeToken,setOneTimeToken]=useState("");
  const canWrite=Boolean(user?.platform_admin||user?.memberships?.some(m=>m.organization_id===organizationId&&m.role==="org_admin"));

  const reload=useCallback(async()=>{
    if(!organizationId){setSources([]);setCatalogs([]);setWorkers([]);return;}
    const [sourceRows,catalogRows,workerRows]=await Promise.all([
      api(API+"/monitoring/data-sources?organization_id="+organizationId),
      api(API+"/rule-catalogs?organization_id="+organizationId),
      canWrite?api(API+"/remote-probes/workers?organization_id="+organizationId):Promise.resolve([])
    ]);
    setSources(sourceRows);setCatalogs(catalogRows);setWorkers(workerRows);
    setSourceId(previous=>sourceRows.some(r=>r.id===previous)?previous:(sourceRows[0]?.id||""));
    setWorkerId(previous=>workerRows.some(r=>r.id===previous)?previous:(workerRows[0]?.id||""));
  },[organizationId,canWrite]);

  useEffect(()=>{reload().catch(e=>setError(e.message));setSelectedRules([]);setPreview(null);setActivation(null);},[reload]);

  async function run(action,onSuccess){
    setBusy(true);setError("");setMessage("");
    try{const result=await action();onSuccess?.(result);return result;}
    catch(e){setError(e.message||"Operation failed");return null;}
    finally{setBusy(false);}
  }
  function makeRule(event){
    event.preventDefault();
    let parsed;
    try{parsed=JSON.parse(definition);}catch{setError("Rule must contain valid JSON");return;}
    run(()=>api(API+"/rule-catalogs",{method:"POST",body:JSON.stringify({
      organization_id:organizationId,kind,name:ruleName.trim(),definition:parsed})}),
      async result=>{setMessage("Versioned "+kind+" rule created.");setSelectedRules(ids=>[...ids,result.versions[0].id]);await reload();});
  }
  async function doPreview(){
    if(!sourceId||!workerId){setError("Choose a Data Source and approved remote worker.");return;}
    const payload={remote_worker_id:workerId,rule_version_ids:selectedRules,include_templates:includeTemplates};
    await run(()=>api(API+"/data-sources/"+sourceId+"/activation-preview",{
      method:"POST",body:JSON.stringify(payload)}),result=>{setPreview(result);setMessage("Activation preview validated; no collector changed.");});
  }
  async function doActivate(){
    if(!preview){setError("Run activation preview first.");return;}
    const payload={remote_worker_id:workerId,rule_version_ids:selectedRules,include_templates:includeTemplates};
    await run(()=>api(API+"/data-sources/"+sourceId+"/activations",{
      method:"POST",body:JSON.stringify(payload)}),result=>{
      setActivation(result);setPreview(null);
      setMessage(result.changed?"Collector and rule bindings activated. Health remains unknown until evidence arrives.":"Configuration already active — no duplicate collector created.");
    });
  }
  async function deactivate(){
    if(!window.confirm("Deactivate monitoring for this Data Source and cancel pending remote jobs?"))return;
    await run(()=>api(API+"/data-sources/"+sourceId+"/deactivation",{method:"POST"}),result=>{
      setActivation(result);setPreview(null);setMessage("Monitoring disabled; history preserved.");
    });
  }
  async function enroll(event){
    event.preventDefault();setOneTimeToken("");
    await run(async()=>{
      const created=await api(API+"/auth/workers",{method:"POST",body:JSON.stringify({
        organization_id:organizationId,name:enrollName.trim(),expires_in_days:30})});
      try{await api(API+"/remote-probes/workers/"+created.id+"/network-policy",{method:"PUT",
        body:JSON.stringify({allowed_hosts:[enrollHost.trim()],allowed_cidrs:[enrollCIDR.trim()]})});}
      catch(e){throw new Error("Worker identity created but network policy rejected; revoke worker "+created.id+" and retry: "+e.message);}
      return created;
    },async result=>{setOneTimeToken(result.worker_token);setMessage("Worker registered. Copy token once into a protected agent secret store.");await reload();});
  }

  async function saveNewRuleVersion(event){
    event.preventDefault();
    let parsed;
    try{parsed=JSON.parse(editDefinition);}catch{setError("Enter valid JSON for the new rule version.");return;}
    await run(()=>api(API+"/rule-catalogs/"+editRule+"/versions",{method:"POST",body:JSON.stringify({definition:parsed})}),
      async result=>{setMessage("Immutable rule version "+result.version+" created. Review and select it before reactivation.");setEditRule("");setEditDefinition("");setPreview(null);await reload();});
  }
  async function refreshDiagnostics(){
    if(!sourceId)return;
    setDiagBusy(true);
    try{
      const details=await api(API+"/data-sources/"+sourceId+"/diagnostics");
      setDiagnostics(details);
    }catch(e){setDiagnostics(null);setError(e.message||"Could not load monitoring diagnostics");}
    finally{setDiagBusy(false);}
  }
  useEffect(()=>{
    setDiagnostics(null);
    if(!sourceId)return;
    refreshDiagnostics();
    const timer=window.setInterval(refreshDiagnostics,15000);
    return()=>window.clearInterval(timer);
  },[sourceId]);
  const versionRows=catalogs.flatMap(c=>c.versions.map(v=>({id:v.id,catalog:c,version:v})));
  function setType(next){setKind(next);setDefinition(JSON.stringify(DEFAULTS[next],null,2));setRuleName(next.toLowerCase()+"-rule");}
  return <div className="monitoring-setup">
    <div className="page-heading"><div><h1>Monitoring Setup</h1>
      <p>Independent versioned rules → approved collector → activation → verified evidence</p></div></div>
    {!organizationId&&<p className="card">Choose an organization first.</p>}
    {error&&<div className="error-box" role="alert">{error}</div>}
    {message&&<div className="card" role="status">{message}</div>}
    <section className="card monitoring-setup-panel">
      <h2>1. Select a Data Source and private-network worker</h2>
      <div className="monitoring-setup-grid">
        <label>Data Source<select value={sourceId} onChange={e=>{setSourceId(e.target.value);setPreview(null);setActivation(null);}}>
          <option value="">Select resource</option>{sources.map(s=><option key={s.id} value={s.id}>{s.name} · {s.source_type}</option>)}
        </select></label>
        <label>Approved remote worker<select value={workerId} onChange={e=>{setWorkerId(e.target.value);setPreview(null);}}>
          <option value="">Select worker</option>{workers.map(w=><option key={w.id} value={w.id}>{w.name} · {w.allowed_hosts.join(", ")||"no hosts"}</option>)}
        </select></label>
      </div>
      <p className="monitoring-helper">Remote workers must be enrolled and assigned explicit hostname/CIDR policies. A configured resource is not automatically monitored.</p>
    </section>
    <section className="card monitoring-setup-panel">
      <h2>2. Choose independent Metric, Log and Alert Rules</h2>
      <div className="monitoring-rule-list">
        {versionRows.map(({id,catalog,version})=><label className="monitoring-rule-option" key={id}>
          <input disabled={!canWrite} type="checkbox" checked={selectedRules.includes(id)} onChange={e=>{
            setSelectedRules(old=>e.target.checked?[...old,id]:old.filter(x=>x!==id));setPreview(null);
          }}/>
          <b>{catalog.kind}</b><span>{catalog.name}</span><small>Version {version.version}</small>
        </label>)}
        {!versionRows.length&&<p className="monitoring-helper">No rule versions yet. Create a Metric Rule to get started.</p>}
      </div>
      {canWrite&&<div className="monitoring-rule-editor">
        <h3>Revise an existing rule (new immutable version)</h3>
        <label>Rule catalog
          <select value={editRule} onChange={e=>{
            setEditRule(e.target.value);
            const catalog=catalogs.find(c=>c.id===e.target.value);
            setEditDefinition(catalog?JSON.stringify(catalog.versions.at(-1)?.definition||{},null,2):"");
          }}>
            <option value="">Choose an existing catalog</option>
            {catalogs.map(c=><option key={c.id} value={c.id}>{c.kind} · {c.name} · latest v{c.versions.at(-1)?.version||1}</option>)}
          </select>
        </label>
        {editRule&&<form onSubmit={saveNewRuleVersion}>
          <p className="monitoring-helper">Existing versions remain unchanged. Activation continues using the pinned selected version until explicitly reapplied.</p>
          <label>Next version JSON<textarea rows={6} spellCheck={false} value={editDefinition} onChange={e=>setEditDefinition(e.target.value)}/></label>
          <button disabled={busy||!editDefinition.trim()} className="primary-button">Create next version</button>
        </form>}
      </div>}
      <label className="monitoring-rule-option"><input type="checkbox" checked={includeTemplates} onChange={e=>{setIncludeTemplates(e.target.checked);setPreview(null);}}/>
        Include attached Monitoring Template bundles</label>
      {canWrite&&<form onSubmit={makeRule} className="monitoring-rule-editor">
        <h3>Create independent rule</h3>
        <div className="monitoring-setup-grid">
          <label>Rule type<select value={kind} onChange={e=>setType(e.target.value)}>{kinds.map(k=><option key={k}>{k}</option>)}</select></label>
          <label>Catalog name<input required maxLength={160} value={ruleName} onChange={e=>setRuleName(e.target.value)}/></label>
        </div>
        <label>Rule definition (JSON)<textarea rows={5} spellCheck={false} value={definition} onChange={e=>setDefinition(e.target.value)}/></label>
        <button className="primary-button" disabled={busy||!organizationId}>Save immutable rule v1</button>
      </form>}
    </section>
    <section className="card monitoring-setup-panel">
      <h2>3. Preview and activate operational monitoring</h2>
      <div className="monitoring-setup-actions">
        <button disabled={!canWrite||busy||!sourceId||!workerId} onClick={doPreview}>Validate & Preview</button>
        <button disabled={!canWrite||busy||!preview} className="primary-button" onClick={doActivate}>Activate monitoring</button>
        <button disabled={!canWrite||busy||!sourceId} onClick={deactivate}>Deactivate</button>
      </div>
      {preview&&<div className="monitoring-preview"><b>{preview.status}</b>
        <p>Collector: {preview.plan.collector.name} · {preview.plan.collector.interval_seconds}s · {preview.plan.rules.length} rules</p>
        <p>Target: {preview.plan.collector.configuration.url}</p>
        <p>Activation means scheduled collection is configured. Target health remains UNKNOWN until fresh evidence arrives.</p>
      </div>}
      {activation&&<div className="monitoring-preview" role="status">Monitoring state: <b>{activation.status}</b>
        {activation.collector_id&&<p>Provisioned collector ID: <code>{activation.collector_id}</code></p>}</div>}
    </section>
    <section className="card monitoring-setup-panel">
      <div className="monitoring-setup-actions"><h2>4. Collector diagnostics and activation progress</h2>
        <button type="button" disabled={!sourceId||diagBusy} onClick={refreshDiagnostics}>{diagBusy?"Refreshing…":"Refresh diagnostics"}</button>
      </div>
      {!diagnostics&&<p className="monitoring-helper">Select a Data Source to inspect actual collector state. No evidence is never reported as healthy.</p>}
      {diagnostics&&<div className="monitoring-preview" data-testid="monitoring-diagnostics">
        <p><b>Activation:</b> {diagnostics.activation.status} · revision {diagnostics.activation.version}</p>
        <p><b>Monitoring:</b> {diagnostics.health} · freshness {diagnostics.freshness}</p>
        {diagnostics.collector&&<>
          <p><b>Collector:</b> {diagnostics.collector.status} · {diagnostics.collector.enabled?"enabled":"disabled"} · interval {diagnostics.collector.interval_seconds}s</p>
          <p><b>Last sample:</b> {diagnostics.collector.last_run_at||"Never collected"}</p>
          <p><b>Next scheduled:</b> {diagnostics.collector.next_run_at||"Not scheduled"}</p>
          {diagnostics.collector.last_error&&<p role="alert"><b>Collector issue:</b> {diagnostics.collector.last_error}</p>}
        </>}
        <p><b>Evidence:</b> {diagnostics.metric_sample_count} metric samples · {diagnostics.open_alert_count} open alerts</p>
        {diagnostics.latest_evidence&&<p><b>Latest HTTP evidence:</b> {diagnostics.latest_evidence.outcome} · HTTP {diagnostics.latest_evidence.http_status??"N/A"} · {diagnostics.latest_evidence.response_time_ms??"N/A"} ms</p>}
        <h3>Recent job leases</h3>
        {diagnostics.jobs.length?<ul>{diagnostics.jobs.map(job=><li key={job.id}>{job.state} · attempts {job.attempts} · {new Date(job.planned_for).toLocaleString()}</li>)}</ul>:<p>No remote jobs dispatched yet.</p>}
      </div>}
    </section>
    {user?.platform_admin&&<section className="card monitoring-setup-panel">
      <h2>Optional — Enroll a private-network agent</h2>
      <form onSubmit={enroll} className="monitoring-rule-editor">
        <div className="monitoring-setup-grid">
          <label>Agent name<input required value={enrollName} onChange={e=>setEnrollName(e.target.value)}/></label>
          <label>Exact allowed hostname<input required value={enrollHost} onChange={e=>setEnrollHost(e.target.value)}/></label>
          <label>Approved CIDR<input required value={enrollCIDR} onChange={e=>setEnrollCIDR(e.target.value)}/></label>
        </div>
        <button className="primary-button" disabled={busy||!organizationId}>Create worker and network policy</button>
      </form>
      {oneTimeToken&&<div className="monitoring-preview">
        <b>One-time worker token (not stored in the browser)</b>
        <p>Copy directly into a secure secret store. This token cannot be retrieved after leaving this screen.</p>
        <input readOnly type="password" value={oneTimeToken} aria-label="One-time worker token"/>
        <button onClick={()=>navigator.clipboard?.writeText(oneTimeToken)}>Copy token</button>
        <button onClick={()=>setOneTimeToken("")}>Clear from screen</button>
      </div>}
    </section>}
  </div>;
}
