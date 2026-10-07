import StatusBadge from "./StatusBadge";

export default function JobDetailsDrawer({ job, details, onClose }) {
  if (!job) return null;

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer">
        <div className="drawer-header">
          <div>
            <div className="eyebrow">JOB ORDER HISTORY · {job.id}</div>
            <h2>{job.name}</h2>
            <StatusBadge status={job.status} />
          </div>
          <button className="close-button" onClick={onClose} aria-label="Close drawer">×</button>
        </div>

        <section className="drawer-section">
          <h3>Execution Summary</h3>
          <div className="summary-grid">
            {[
              ["Job Order ID", job.jobOrderId],
              ["Organization", details?.organization ?? "ABC Corporation"],
              ["VM / Server", job.server],
              ["Environment", job.environment],
              ["Pentaho", details?.pentahoInstance ?? "PENTAHO-PROD-01"],
              ["Execution", job.executionType],
              ["Start", `${job.start} IST`],
              ["End / Failure", job.end ? `${job.end} IST` : "Running"],
              ["Duration", job.duration],
              ["Expected Runtime", job.expectedRuntime],
              ["SLA", job.sla],
              ["SLA Status", details?.slaStatus ?? "ON TRACK"],
              ["Incident", job.incident ?? "—"],
              ["Detected", details?.detected ?? "—"],
            ].map(([label, value]) => (
              <div className="kv" key={label}><span>{label}</span><b>{value}</b></div>
            ))}
          </div>
        </section>

        {job.status === "FAILED" && (
          <>
            <section className="drawer-section">
              <h3>Failure Diagnosis</h3>
              <div className="kv"><span>Failed Step</span><b>{job.failedStep}</b></div>
              <pre className="error-box">PentahoError: {job.error}</pre>
              <div className="kv"><span>Suspected Cause</span><b>{details?.suspectedCause}</b></div>
              <div className="kv"><span>Confidence</span><b>{details?.confidence}</b></div>
            </section>

            <section className="drawer-section">
              <h3>Execution Timeline</h3>
              {details?.timeline?.map(([time, event]) => <div className="timeline-item" key={time + event}><b>{time}</b><span>{event}</span></div>)}
            </section>

            <section className="drawer-section">
              <h3>Step-level Execution</h3>
              {details?.steps?.map(([step, status]) => (
                <div className="list-row" key={step}><span>{step}</span><StatusBadge status={status} /></div>
              ))}
            </section>

            <section className="drawer-section">
              <h3>Related Health</h3>
              <div className="summary-grid">
                <div className="kv"><span>Database</span><b className="critical-text">{details?.database}</b></div>
                <div className="kv"><span>CPU</span><b>{details?.cpu}</b></div>
                <div className="kv"><span>RAM</span><b>{details?.ram}</b></div>
                <div className="kv"><span>Network</span><b className="healthy-text">{details?.network}</b></div>
              </div>
            </section>
          </>
        )}

        <section className="drawer-section">
          <h3>Alert & Incident History</h3>
          {[
            ["08:05:55", "Failure detected", "CRITICAL"],
            ["08:06:01", "PagerDuty triggered", "PD-12345"],
            ["08:06:05", "ServiceNow incident created", job.incident ?? "—"],
            ["08:06:07", "Email notification sent", "SLM Operations"],
            ["08:08:14", "PagerDuty acknowledged", "Operator A"],
          ].map(([time, event, value]) => (
            <div className="list-row" key={time + event}><span><b>{time}</b> · {event}</span><span className="muted small">{value}</span></div>
          ))}
        </section>

        <section className="drawer-section">
          <h3>Recent History · Same Job Order</h3>
          {[
            ["07-Oct 08:04", "FAILED", "Database timeout"],
            ["06-Oct 08:00", "SUCCESS", "18m"],
            ["05-Oct 08:00", "SUCCESS", "19m"],
            ["04-Oct 08:00", "SUCCESS", "21m"],
          ].map(([time, status, value]) => (
            <div className="list-row" key={time}><span>{time} · <b>{status}</b></span><span className="muted small">{value}</span></div>
          ))}
        </section>

        <section className="drawer-section">
          <h3>Investigation</h3>
          <div className="summary-grid">
            <div className="kv"><span>Status</span><b className="warning-text">INVESTIGATING</b></div>
            <div className="kv"><span>Operator</span><b>Operator A</b></div>
            <div className="kv"><span>Started</span><b>08:08:14 IST</b></div>
            <div className="kv"><span>Notes</span><b>{details?.notes?.length ?? 0}</b></div>
          </div>
          {details?.notes?.map(([time, operator, note]) => (
            <div className="note" key={time + note}><b>{time} · {operator}</b><div>{note}</div></div>
          ))}
          <textarea className="note-input" placeholder="Add chronological operator note..." />
          <button className="primary-button" onClick={() => window.alert("Prototype: note persistence will be connected to the backend API.")}>Add Note</button>
        </section>

        <section className="drawer-section">
          <h3>Resolution</h3>
          <div className="kv"><span>Root Cause</span><b>PENDING</b></div>
          <div className="kv"><span>Recovery</span><b>Performed outside OpsControl by the appropriate team.</b></div>
        </section>
      </aside>
    </>
  );
}