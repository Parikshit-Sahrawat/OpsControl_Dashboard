import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
import useDialogFocus from "./useDialogFocus";
import ThemeToggle from "./ThemeToggle";
import "./personal-workspace.css";

const docs = "https://github.com/Parikshit-Sahrawat/OpsControl_Dashboard/blob/main/docs/";

export default function PersonalWorkspace({ kind, user, onClose }) {
  const ref = useRef(null);
  const generation = useRef(0);
  const [preference, setPreference] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [retry, setRetry] = useState(0);
  const allowed = hasPermission(user, "alerts.view");
  const title = kind === "profile" ? "My profile" : "Help and operator guides";
  useDialogFocus(ref, true, onClose);
  useEffect(() => {
    const current = ++generation.current;
    const request = new AbortController();
    setPreference(null); setError(""); setSaved(false); setBusy(false);
    if (kind === "profile" && allowed) {
      control("/api/v1/notifications/preferences", "GET", undefined, { signal: request.signal })
        .then(value => { if (generation.current === current) setPreference(value.in_app); })
        .catch(e => { if (!request.signal.aborted && generation.current === current) setError(e.message); });
    }
    return () => { generation.current++; request.abort(); };
  }, [kind, allowed, user?.id, user?.authorization_revision, retry]);
  async function save() {
    if (busy || preference === null) return;
    const current = generation.current;
    setBusy(true); setSaved(false); setError("");
    try {
      const value = await control("/api/v1/notifications/preferences", "PUT", { in_app: preference });
      if (generation.current === current) { setPreference(value.in_app); setSaved(true); }
    } catch (e) {
      if (generation.current === current) setError(e.message);
    } finally {
      if (generation.current === current) setBusy(false);
    }
  }
  return createPortal(<div className="modal-backdrop personal-backdrop">
    <section ref={ref} role="dialog" aria-modal="true" aria-label={title} className="personal-workspace">
      <div className="personal-heading"><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Close personal workspace">Close</button></div>
      {kind === "profile" ? <>
        <h3>Account</h3>
        <dl><dt>Username</dt><dd>{user?.username}</dd><dt>Account access</dt><dd>{user?.platform_admin ? "Platform administrator" : "Assigned roles and customer boundaries"}</dd></dl>
        <p>Contact your access administrator for account details, password resets or role changes. Signing out ends this browser session.</p>
        <h3>Appearance</h3><ThemeToggle />
        <p>Your appearance preference is saved in this browser when browser storage is available.</p>
        <h3>Personal notifications</h3>
        {allowed ? <>
          {preference === null && !error && <p role="status">Loading your preferences…</p>}
          {preference !== null && <>
            <label><input type="checkbox" checked={preference} disabled={busy} onChange={e => { setPreference(e.target.checked); setSaved(false); }} /> Receive in-app notifications</label>
            <p>This preference applies to your account. It does not change monitoring rules or other users’ destinations.</p>
            <button type="button" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save notification preference"}</button>
          </>}
          {error && <div role="alert"><p>{error}</p>{preference === null && <button type="button" onClick={() => setRetry(n => n + 1)}>Retry preferences</button>}</div>}
          {saved && <p role="status">Notification preference saved.</p>}
        </> : <p>Notification preferences require alerts viewing permission. Ask your access administrator if you need this access.</p>}
      </> : <>
        <p>Use Resource Management to configure resources. Operations pages display collected evidence and monitoring health.</p>
        <h3>Getting started</h3>
        <ol><li>Select an authorized customer organization.</li><li>Register a supported compute instance, API endpoint or data pipeline in Resource Management.</li><li>Configure templates and independent collection methods. Keep credentials in approved secret references.</li><li>Validate readiness and review actual telemetry before activation. Registration alone does not prove monitoring health.</li></ol>
        <h3>Operator guides</h3>
        <ul>
          <li><a href={docs + "AGENT_INSTALL_OPERATOR.md"} target="_blank" rel="noopener noreferrer">Windows and Linux agent installation</a></li>
          <li><a href={docs + "ARCH_001_V16.md"} target="_blank" rel="noopener noreferrer">Collection methods, supported capabilities and readiness</a></li>
          <li><a href={docs + "verification/dev052/PENTAHO_CERTIFICATION.md"} target="_blank" rel="noopener noreferrer">Pentaho compatibility and read-only certification prerequisites</a></li>
        </ul>
        <h3>Frequently asked questions</h3>
        <details><summary>Why is my resource not visible?</summary><p>Check your explicit organization selection, environment filters and assigned permissions. An empty authorized view does not establish that a resource was deleted.</p></details>
        <details><summary>Why is activation blocked?</summary><p>Read the reported readiness diagnostics. Missing telemetry, unsupported collection methods, expired credentials or unverified native capabilities must be resolved. Do not bypass readiness checks.</p></details>
        <details><summary>Can OpsControl run or change Pentaho jobs?</summary><p>Pentaho monitoring is read-only. Job execution, scheduler changes and provider administration remain outside the monitoring workflow.</p></details>
        <details><summary>What should I include in a support report?</summary><p>Include the resource ID, timestamp, application revision, expected and actual behavior, and redacted diagnostics. Never include passwords, tokens or customer payloads.</p></details>
      </>}
    </section>
  </div>, document.body);
}
