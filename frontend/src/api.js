const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(API_BASE + path, { headers: { "Content-Type": "application/json", ...(options.headers || {}) }, ...options });
  if (!response.ok) {
    let message = "API request failed";
    try { const body = await response.json(); message = body.detail || message; } catch {}
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}
const secondsToText = (seconds) => {
  if (seconds == null) return null;
  const m = Math.floor(seconds / 60), s = seconds % 60;
  return m ? (m + "m " + String(s).padStart(2,"0") + "s") : (s + "s");
};
const timeText = (value) => value ? new Date(value).toLocaleTimeString("en-IN", { hour12: false }) : null;
export function mapExecution(item) {
  return { id:item.id, jobOrderId:item.job_order_id, name:item.job_name, server:item.server, environment:item.environment, executionType:item.execution_type, start:timeText(item.started_at), end:timeText(item.ended_at), duration:item.started_at && item.ended_at ? secondsToText(Math.max(0,(new Date(item.ended_at)-new Date(item.started_at))/1000)) : null, expectedRuntime:secondsToText(item.expected_runtime_seconds), sla:secondsToText(item.sla_seconds), status:item.status, failedStep:item.failed_step, incident:item.incident_number };
}
export async function fetchExecutions(params = {}) {
  const query = new URLSearchParams();
  for (const [key,value] of Object.entries(params)) {
    if (Array.isArray(value)) value.forEach(item => query.append(key, item));
    else if (value && value !== "All") query.set(key,value);
  }
  return (await request("/api/v1/etl/executions?" + query.toString())).map(mapExecution);
}
export function fetchExecution(id) { return request("/api/v1/etl/executions/" + id); }
export function fetchInvestigation(id) { return request("/api/v1/etl/executions/" + id + "/investigation"); }
export function transitionInvestigation(id,newStatus,operator="Operator A",comment=null) { return request("/api/v1/etl/executions/" + id + "/investigation/transitions",{method:"POST",body:JSON.stringify({new_status:newStatus,operator,comment})}); }
export function addInvestigationNote(id,text,operator="Operator A",evidence_reference=null) { return request("/api/v1/etl/executions/" + id + "/investigation/notes",{method:"POST",body:JSON.stringify({operator,text,evidence_reference})}); }

export const fetchDataSources=(params={})=>request("/api/v1/monitoring/data-sources?"+new URLSearchParams(params).toString());
export const fetchCollectors=(params={})=>request("/api/v1/monitoring/collectors?"+new URLSearchParams(params).toString());
export const fetchMetrics=(params={})=>request("/api/v1/monitoring/metrics?"+new URLSearchParams(params).toString());
export const fetchLogSources=(params={})=>request("/api/v1/monitoring/logs?"+new URLSearchParams(params).toString());
export const createDataSource=p=>request("/api/v1/monitoring/data-sources",{method:"POST",body:JSON.stringify(p)});
export const updateDataSource=(id,p)=>request("/api/v1/monitoring/data-sources/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const deleteDataSource=id=>request("/api/v1/monitoring/data-sources/"+id,{method:"DELETE"});
export const createCollector=p=>request("/api/v1/monitoring/collectors",{method:"POST",body:JSON.stringify(p)});
export const updateCollector=(id,p)=>request("/api/v1/monitoring/collectors/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const deleteCollector=id=>request("/api/v1/monitoring/collectors/"+id,{method:"DELETE"});
export const createMetric=p=>request("/api/v1/monitoring/metrics",{method:"POST",body:JSON.stringify(p)});
export const updateMetric=(id,p)=>request("/api/v1/monitoring/metrics/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const deleteMetric=id=>request("/api/v1/monitoring/metrics/"+id,{method:"DELETE"});
export const createLogSource=p=>request("/api/v1/monitoring/logs",{method:"POST",body:JSON.stringify(p)});
export const updateLogSource=(id,p)=>request("/api/v1/monitoring/logs/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const deleteLogSource=id=>request("/api/v1/monitoring/logs/"+id,{method:"DELETE"});

export const fetchOrganizations=(params={})=>request("/api/v1/monitoring/organizations?"+new URLSearchParams(params).toString());

export const fetchAlertRules=(params={})=>request("/api/v1/monitoring/alert-rules?"+new URLSearchParams(params).toString());
export const createAlertRule=p=>request("/api/v1/monitoring/alert-rules",{method:"POST",body:JSON.stringify(p)});
export const updateAlertRule=(id,p)=>request("/api/v1/monitoring/alert-rules/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const deleteAlertRule=id=>request("/api/v1/monitoring/alert-rules/"+id,{method:"DELETE"});

export const fetchExecutionCorrelation=id=>request("/api/v1/etl/executions/"+id+"/correlation");
export const analyzeExecutionCorrelation=(id,windowBeforeSeconds=900,windowAfterSeconds=900)=>request("/api/v1/etl/executions/"+id+"/correlation?window_before_seconds="+windowBeforeSeconds+"&window_after_seconds="+windowAfterSeconds,{method:"POST"});


export const fetchMonitoringTemplates=(params={})=>request("/api/v1/monitoring/templates?"+new URLSearchParams(params).toString());
export const createMonitoringTemplate=p=>request("/api/v1/monitoring/templates",{method:"POST",body:JSON.stringify(p)});
export const updateMonitoringTemplate=(id,p)=>request("/api/v1/monitoring/templates/"+id,{method:"PATCH",body:JSON.stringify(p)});
export const fetchMonitoringTemplateVersions=id=>request("/api/v1/monitoring/templates/"+id+"/versions");
export const deleteMonitoringTemplate=id=>request("/api/v1/monitoring/templates/"+id,{method:"DELETE"});
export const fetchDataSourceTemplates=id=>request("/api/v1/monitoring/data-sources/"+id+"/templates");
export const attachDataSourceTemplate=(id,p)=>request("/api/v1/monitoring/data-sources/"+id+"/templates",{method:"POST",body:JSON.stringify(p)});
export const updateDataSourceTemplate=(id,templateId,p)=>request("/api/v1/monitoring/data-sources/"+id+"/templates/"+templateId,{method:"PATCH",body:JSON.stringify(p)});
export const detachDataSourceTemplate=(id,templateId)=>request("/api/v1/monitoring/data-sources/"+id+"/templates/"+templateId,{method:"DELETE"});
export const fetchEffectiveDataSourceConfiguration=id=>request("/api/v1/monitoring/data-sources/"+id+"/effective-configuration");

