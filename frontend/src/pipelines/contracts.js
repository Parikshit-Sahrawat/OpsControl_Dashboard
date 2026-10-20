// Display contracts only. Authorization and evidence adjudication remain server-side.
export const PAGES = {
  inventory: "Pipeline Inventory",
  executions: "Execution History",
  schedules: "Schedule Monitoring",
  evidence: "Evidence Review",
  recovery: "Recovery Tracking",
  incidents: "Incident Correlation",
};
export const CATEGORIES = [
  "AMBIGUOUS_IDENTITY",
  "NATIVE_ALIAS_CONFLICT",
  "RETRY_RELATIONSHIP",
  "EXECUTION_OUTCOME",
  "LEGACY_ADOPTION",
  "RECOVERY_IDENTITY",
];
export const INCIDENT_TRANSITIONS = {
  OPEN: ["ACKNOWLEDGED", "INVESTIGATING"],
  ACKNOWLEDGED: ["INVESTIGATING", "RECOVERY_IN_PROGRESS"],
  INVESTIGATING: ["RECOVERY_IN_PROGRESS"],
  RECOVERY_IN_PROGRESS: ["MONITORING", "INVESTIGATING"],
  MONITORING: ["RESOLVED", "INVESTIGATING"],
  RESOLVED: ["CLOSED", "OPEN"],
  CLOSED: ["OPEN"],
};
export const OUTCOMES = [
  "SUCCESS",
  "SUCCESS_AFTER_RETRY",
  "FAILED",
  "CANCELLED",
  "UNKNOWN",
  "WAITING_FOR_RETRY",
];
export const EXPLANATIONS = {
  UNKNOWN: "No verified conclusion is available.",
  INCOMPLETE: "Required evidence or monitoring coverage is incomplete.",
  PARTIAL: "Only part of the required evidence was observed.",
  REVIEW_REQUIRED: "An authorized investigator must review native evidence.",
  CONFLICTED_EVIDENCE:
    "Conflicting claims remain unresolved; the previous defensible projection is preserved.",
  WAITING_FOR_RETRY:
    "Nonterminal: retry authority has not established final failure.",
  SUCCESS_AFTER_RETRY:
    "Verified scheduler retry succeeded within this logical execution.",
  NO_RUN: "A missed occurrence recorded by the backend schedule evaluator.",
};
export function params(ids, environment, extra = {}) {
  const q = new URLSearchParams();
  [...new Set(ids)].forEach((id) => q.append("organization_id", id));
  if (Array.isArray(environment)) environment.forEach((value) => q.append("environments", value));
  else if (environment) q.set("environment", environment);
  Object.entries(extra).forEach(([k, v]) => {
    if (v !== "" && v !== undefined && v !== null) q.set(k, String(v));
  });
  return q.toString();
}
export const resourcePath = (id) =>
  "/api/v1/unified/resources/" + encodeURIComponent(id);
export const executionPath = (r, h) =>
  resourcePath(r) + "/executions/" + encodeURIComponent(h);
export function outcome(h = {}) {
  if (h.pentaho_lifecycle === "WAITING_FOR_RETRY") return "WAITING_FOR_RETRY";
  if (h.pentaho_resource_id)
    return (
      h.pentaho_outcome ||
      (h.pentaho_lifecycle === "RUNNING" ? "RUNNING" : "UNKNOWN")
    );
  return h.status || "UNKNOWN";
}
export function nativeType(r = {}) {
  const c = r.configuration || {},
    kind = c.workload_kind || r.binding?.workloadKind;
  return (
    kind ||
    c.native_resource_type ||
    c.resource_type ||
    {
      AIRFLOW: "DAG",
      ADF: "Pipeline",
      SSIS: "Package",
      GLUE: "Job",
      TALEND: "Task",
      INFORMATICA: "Task",
      PENTAHO: "Job / transformation (type unreported)",
      NIFI: "Process group / processor (type unreported)",
    }[c.platform] ||
    "Native type unreported"
  );
}
export function reviewActions(r) {
  if (r?.status !== "OPEN") return [];
  const verified =
    r.context?.identity?.completion_evidence === true &&
    r.context?.verification?.claims?.includes("EXECUTION_OUTCOME");
  return [
    "DEFER",
    "REJECT_CLAIM",
    ...(r.category === "EXECUTION_OUTCOME" && verified
      ? ["ACCEPT_VERIFIED_CLAIM"]
      : []),
    ...(r.category === "LEGACY_ADOPTION" ? ["ADOPT_LEGACY"] : []),
  ];
}
export function linkActions(link, userId) {
  return link.status === "PROPOSED"
    ? userId && link.proposed_by !== userId
      ? ["CONFIRM"]
      : []
    : link.status === "CONFIRMED"
      ? ["REVERSE"]
      : [];
}
export function time(value) {
  if (!value) return "Not observed";
  const d = new Date(value);
  return Number.isNaN(d.valueOf())
    ? "Invalid timestamp"
    : d.toISOString().replace("T", " ").replace("Z", " UTC");
}
export function duration(h) {
  if (!h.started_at || !h.ended_at) return "Unknown";
  const s = (new Date(h.ended_at) - new Date(h.started_at)) / 1000;
  return Number.isFinite(s) && s >= 0
    ? `${Math.floor(s / 60)}m ${Math.floor(s % 60)}s`
    : "Unknown";
}
export function scheduleAuthority(w) {
  const snapshot = w.pentaho_authority || {},
    mode = snapshot.selection?.mode || w.evidence?.authority_mode || "UNKNOWN";
  return {
    mode,
    snapshot,
    label:
      mode === "VERIFIED_SCHEDULER"
        ? "Verified native scheduler"
        : mode === "MONITORING_EXPECTATION"
          ? "Configured monitoring expectation"
          : mode === "MANUAL"
            ? "Manual / no expectation"
            : "Unknown schedule authority",
  };
}
export function errorMessage(e) {
  if (e.status === 409)
    return (
      "This record changed or evidence no longer permits this action. Refresh and review the current revision. " +
      e.message
    );
  if (e.status === 403)
    return "Permission denied for this customer and action.";
  if (e.status === 401) return "Your session expired. Sign in again.";
  return e.message || "Monitoring evidence could not be loaded.";
}
export function requestGeneration() {
  let current = 0;
  return {
    next: () => ++current,
    accepts: (n) => n === current,
    invalidate: () => {
      current++;
    },
  };
}
export function binding(resource, integration) {
  const job = integration?.jobs?.find((j) => j.resource_id === resource.id),
    ids = new Set(
      (integration?.associations || [])
        .filter((a) => a.job_id === job?.id)
        .map((a) => a.method_id),
    );
  const methods = (integration?.methods || []).filter((m) => ids.has(m.id));
  return {
    methods,
    sources: (integration?.sources || []).filter((s) =>
      methods.some((m) => m.source_id === s.id),
    ),
    capabilities: (integration?.capabilities || []).filter((c) =>
      methods.some((m) => m.capability_id === c.id),
    ),
    workloadKind: integration?.connections?.find((c) =>
      methods.some((m) => m.connection_id === c.id),
    )?.configuration?.monitoring_context?.workload_kind,
  };
}
