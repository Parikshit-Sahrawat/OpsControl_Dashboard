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
  for (const [key,value] of Object.entries(params)) if (value && value !== "All") query.set(key,value);
  return (await request("/api/v1/etl/executions?" + query.toString())).map(mapExecution);
}
export function fetchExecution(id) { return request("/api/v1/etl/executions/" + id); }
export function fetchInvestigation(id) { return request("/api/v1/etl/executions/" + id + "/investigation"); }
export function transitionInvestigation(id,newStatus,operator="Operator A",comment=null) { return request("/api/v1/etl/executions/" + id + "/investigation/transitions",{method:"POST",body:JSON.stringify({new_status:newStatus,operator,comment})}); }
export function addInvestigationNote(id,text,operator="Operator A",evidence_reference=null) { return request("/api/v1/etl/executions/" + id + "/investigation/notes",{method:"POST",body:JSON.stringify({operator,text,evidence_reference})}); }
