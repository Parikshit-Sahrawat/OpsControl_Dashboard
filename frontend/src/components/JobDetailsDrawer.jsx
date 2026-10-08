import { useEffect, useMemo, useState } from "react";
import StatusBadge from "./StatusBadge";
import { analyzeExecutionCorrelation, fetchExecutionCorrelation } from "../api";

const investigationFlow = ["NEW", "ACKNOWLEDGED", "INVESTIGATING", "ROOT_CAUSE_IDENTIFIED", "RECOVERY_IN_PROGRESS", "MONITORING", "RESOLVED"];
function nextState(state) { const i = investigationFlow.indexOf(state); return i >= 0 && i < investigationFlow.length - 1 ? investigationFlow[i + 1] : null; }

export default function JobDetailsDrawer({ job, details, onClose, onInvestigationChange, onAddNote }) {
  const [note, setNote] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [correlation, setCorrelation] = useState(null);
  const [correlationLoading, setCorrelationLoading] = useState(false);
  const [correlationError, setCorrelationError] = useState("");
  const [analyzingCorrelation, setAnalyzingCorrelation] = useState(false);
  useEffect(() => {
    setNote("");
    setCorrelation(null);
    setCorrelationError("");
    if (!job?.id) return;
    let active = true;
    setCorrelationLoading(true);
    fetchExecutionCorrelation(job.id)
      .then(value => { if (active) setCorrelation(value); })
      .catch(error => { if (active && error?.message !== "Correlation record not found") setCorrelationError(error.message || "Unable to load correlation"); })
      .finally(() => { if (active) setCorrelationLoading(false); });
    return () => { active = false; };
  }, [job?.id]);
  const runCorrelation = async () => {
    setAnalyzingCorrelation(true);
    setCorrelationError("");
    try { setCorrelation(await analyzeExecutionCorrelation(job.id)); }
    catch (error) { setCorrelationError(error.message || "Correlation analysis failed"); }
    finally { setAnalyzingCorrelation(false); }
  };
  if (!job) return null;

  const investigation = details?.investigation ?? { status: job.status === "FAILED" ? "NEW" : null, operator: "—", started: "—", notes: [], transitions: [] };
  const steps = details?.steps ?? [];
  const timeline = details?.timeline ?? [];
  const recentHistory = details?.recentHistory ?? [];
  const incidentHistory = details?.incidentHistory ?? [];
  const isInvestigable = ["FAILED", "NO_RUN", "NO_RESPONSE", "LONG_RUNNING"].includes(job.status);
  const next = isInvestigable ? nextState(investigation.status) : null;
  const runtimeSummary = useMemo(() => {
    if (details?.slaStatus) return details.slaStatus;
    if (job.status === "SUCCESS") return "MET";
    if (job.status === "FAILED") return "NOT MET";
    if (job.status === "LONG_RUNNING") return "AT RISK";
    return "ON TRACK";
  }, [job.status, details?.slaStatus]);

  const addNote = async () => {
    if (!note.trim() || !onAddNote) return;
    setSavingNote(true);
    try { await onAddNote(job.id, note.trim()); setNote(""); } finally { setSavingNote(false); }
  };

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true" aria-label={`${job.name} execution details`}>
        <div className="drawer-header">
          <div><div className="eyebrow">JOB ORDER HISTORY · {job.id}</div><h2>{job.name}</h2><div className="drawer-status-row"><StatusBadge status={job.status}/><span className="execution-type">{job.executionType}</span></div></div>
          <button className="close-button" onClick={onClose} aria-label="Close drawer">×</button>
        </div>

        <section className="drawer-section"><h3>Execution Summary</h3><div className="summary-grid">
          {[
            ["Job Order ID", job.jobOrderId], ["Organization", details?.organization ?? "ABC Corporation"], ["VM / Server", job.server],
            ["Environment", job.environment], ["Pentaho", details?.pentahoInstance ?? "PENTAHO-PROD-01"], ["Execution", job.executionType],
            ["Start", job.start ? `${job.start} IST` : "Not started"], ["End / Failure", job.end ? `${job.end} IST` : "Not completed"],
            ["Duration", job.duration ?? "—"], ["Expected Runtime", job.expectedRuntime ?? "—"], ["SLA", job.sla ?? "—"],
            ["SLA Status", runtimeSummary], ["Incident", job.incident ?? "—"], ["Detected", details?.detected ?? "—"], ["Last Update", details?.lastUpdate ?? "—"],
          ].map(([label, value]) => <div className="kv" key={label}><span>{label}</span><b>{value}</b></div>)}
        </div></section>

        {job.status === "FAILED" && <section className="drawer-section"><h3>Failure Diagnosis</h3>
          <div className="diagnosis-grid">
            <div><span>Failed Step</span><b>{job.failedStep ?? "—"}</b></div><div><span>Failure Category</span><b>{details?.failureCategory ?? "Pending"}</b></div>
            <div><span>Suspected Cause</span><b>{details?.suspectedCause ?? "Pending"}</b></div><div><span>Confidence</span><b>{details?.confidence ?? "—"}</b></div>
          </div>
          <pre className="error-box">PentahoError: {job.error ?? "No source error reported."}</pre>
          <div className="source-fact"><span>Source fact</span> OpsControl analysis is shown separately from Pentaho-reported data and does not overwrite historical evidence.</div>
        </section>}

        {(job.status === "NO_RUN" || job.status === "LONG_RUNNING") && <section className="drawer-section"><h3>Monitoring Diagnosis</h3>
          <div className="diagnosis-grid">
            <div><span>Expected Window</span><b>{details?.expectedWindow ?? "Configured window unavailable"}</b></div><div><span>Grace Period</span><b>{details?.gracePeriod ?? "Configured value unavailable"}</b></div>
            <div><span>Expected Runtime</span><b>{job.expectedRuntime ?? "—"}</b></div><div><span>SLA</span><b>{job.sla ?? "—"}</b></div>
          </div>
          <div className="source-fact">{job.status === "NO_RUN" ? "No execution was detected after the configured expected window and grace period." : "Execution has exceeded expected runtime but remains within the configured SLA window."}</div>
        </section>}

        <section className="drawer-section"><h3>Execution Timeline</h3>
          {timeline.length ? timeline.map((item, i) => <div className="timeline-item" key={item.time + item.event + i}><b>{item.time}</b><span>{item.event}<small>{item.source ?? ""}</small></span></div>) : <div className="empty-inline">No timeline events have been reported for this execution.</div>}
        </section>

        <section className="drawer-section"><h3>Step-level Execution</h3>
          {steps.length ? steps.map((step, i) => <div className="step-row" key={step.name + i}><div><b>{step.name}</b><small>{step.type ?? "Pentaho step"}{step.duration ? ` · ${step.duration}` : ""}</small></div><StatusBadge status={step.status}/></div>) : <div className="empty-inline">Step-level data is not available from the current source.</div>}
        </section>

        {details?.relatedHealth && <section className="drawer-section"><h3>Related Health</h3><div className="summary-grid">
          {Object.entries(details.relatedHealth).map(([label, value]) => <div className="kv" key={label}><span>{label}</span><b>{value}</b></div>)}
        </div></section>}
        <section className="drawer-section"><div className="section-heading-row"><h3>Related Health / Correlation</h3><button className="filter-button" disabled={correlationLoading || analyzingCorrelation} onClick={runCorrelation}>{analyzingCorrelation ? "Analyzing…" : "Analyze"}</button></div>
          {correlationLoading && <div className="empty-inline">Loading correlation evidence…</div>}
          {!correlationLoading && correlation && <><div className="summary-grid">
            <div className="kv"><span>Primary Evidence</span><b>{correlation.primary_category}</b></div>
            <div className="kv"><span>Confidence</span><b>{correlation.confidence}</b></div>
            <div className="kv"><span>Evidence Items</span><b>{correlation.evidence_count}</b></div>
            <div className="kv"><span>Analysis Version</span><b>{correlation.analysis_version}</b></div>
          </div>
          <div className="source-fact">{correlation.summary}</div>
          {correlation.evidence?.slice(0, 12).map(item => <div className="list-row" key={item.id}><span><b>{item.evidence_type}</b> · {item.relationship}</span><span className="muted small">{item.severity ?? "—"} · {new Date(item.observed_at).toLocaleTimeString("en-IN", { hour12: false })}</span></div>)}
          {correlation.evidence?.length > 12 && <div className="empty-inline">Showing the first 12 evidence items in the drawer.</div>}
          </>}
          {!correlationLoading && !correlation && !correlationError && <div className="empty-inline">No correlation analysis has been run for this execution.</div>}
          {correlationError && <div className="error-box">{correlationError}</div>}
        </section>

        <section className="drawer-section"><h3>Alert & Incident History</h3>
          {incidentHistory.length ? incidentHistory.map((item, i) => <div className="list-row" key={item.time + item.event + i}><span><b>{item.time}</b> · {item.event}</span><span className="muted small">{item.reference ?? "—"}</span></div>) : <div className="empty-inline">No operational alert or incident events recorded.</div>}
        </section>

        <section className="drawer-section"><h3>Recent History · Same Job Order</h3>
          {recentHistory.length ? recentHistory.map((item, i) => <div className="list-row" key={item.time + i}><span>{item.time} · <b>{item.status}</b></span><span className="muted small">{item.duration ?? item.reason ?? "—"} {item.incident ? `· ${item.incident}` : ""}</span></div>) : <div className="empty-inline">No previous execution history available.</div>}
        </section>

        {isInvestigable && <section className="drawer-section">
          <div className="section-heading-row"><h3>Investigation</h3><span className="investigation-status">{investigation.status}</span></div>
          <div className="summary-grid">
            <div className="kv"><span>Operator</span><b>{investigation.operator}</b></div><div className="kv"><span>Started</span><b>{investigation.started}</b></div>
            <div className="kv"><span>Notes</span><b>{investigation.notes?.length ?? 0}</b></div><div className="kv"><span>Transitions</span><b>{investigation.transitions?.length ?? 0}</b></div>
          </div>
          {investigation.transitions?.map((t, i) => <div className="transition" key={t.timestamp + i}><b>{t.previous} → {t.next}</b><small>{t.timestamp} · {t.operator}{t.comment ? ` · ${t.comment}` : ""}</small></div>)}
          {investigation.notes?.map((n, i) => <div className="note" key={n.timestamp + i}><b>{n.timestamp} · {n.operator}</b><div>{n.text}</div>{n.evidence && <small>Evidence: {n.evidence}</small>}</div>)}
          <textarea className="note-input" value={note} onChange={e => setNote(e.target.value)} placeholder="Add chronological operator note..." />
          <div className="action-row">
            <button className="primary-button" disabled={!note.trim() || savingNote} onClick={addNote}>{savingNote ? "Adding…" : "Add Note"}</button>
            {next && <button className="filter-button" onClick={() => onInvestigationChange?.(job.id, next)}>Move to {next.replaceAll("_", " ")}</button>}
          </div>
          {investigation.status === "RESOLVED" && <div className="resolution-box">Resolution is preserved as an auditable investigation outcome. A successful next execution does not automatically resolve an investigation.</div>}
        </section>}
      </aside>
    </>
  );
}