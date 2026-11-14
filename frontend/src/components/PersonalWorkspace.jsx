import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
import useDialogFocus from "./useDialogFocus";
import ThemeToggle from "./ThemeToggle";
import "./personal-workspace.css";

// Guides ship with the frontend, including subpath and offline deployments.
const docs = import.meta.env.BASE_URL + "docs/";

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
        <p><strong>Self-hosted, customer-managed:</strong> APTron provides monitoring software, secure defaults and deployment guidance. Your organization chooses and operates the hosts, storage, network, account, keys, backups and any cloud provider. APTron does not bill customer infrastructure.</p>
        <h3>Getting started</h3>
        <ol>
          <li>Select an authorized customer organization and environment.</li>
          <li>Choose an approved self-hosted Linux deployment location: on-premises, private cloud, or your own AWS, Azure, GCP or other supported account.</li>
          <li>Register supported resources, configure collection methods, and supply only your organization's approved credential references.</li>
          <li>Validate actual monitoring evidence before activation; a single-host demonstration is not high availability.</li>
        </ol>
        <h3>Documentation</h3>
        <p>Deployment environments, Docker Compose, candidate three-host HA, backup, rollback and recovery responsibilities.</p>
        <ul><li><a href={docs + "self-hosted/DEPLOYMENT_GUIDE.md"} target="_blank" rel="noopener noreferrer">Self-hosted deployment guide — on-premises, AWS, Azure, GCP and private cloud</a></li></ul>
        <h3>Learning</h3>
        <p>Learn infrastructure sizing, cloud versus on-premises cost drivers, customer-managed billing and the use of editable illustrative value sheets. Estimates are not quotes.</p>
        <ul><li><a href={docs + "self-hosted/COST_PLANNING.md"} target="_blank" rel="noopener noreferrer">Infrastructure cost planning and example assumptions</a></li></ul>
        <h3>Training</h3>
        <p>Role-based self-paced exercises for collectors, jobs/workflows, API and Synthetic Monitoring, privacy-safe RUM, security and recovery. Use synthetic data.</p>
        <ul><li><a href={docs + "self-hosted/TRAINING_GUIDE.md"} target="_blank" rel="noopener noreferrer">Self-hosted operations and security learning paths</a></li></ul>
        <h3>Frequently asked questions</h3>
        <details><summary>Does APTron require AWS, Azure or GCP?</summary><p>No. Cloud hosting is optional. Install on customer-operated on-premises Linux infrastructure, private cloud, or a supported customer-owned provider environment. No APTron-operated account is required.</p></details>
        <details><summary>Who pays for servers, cloud resources and backups?</summary><p>Your organization chooses and pays the infrastructure provider. APTron supplies software and documentation; it does not invoice for the provider's infrastructure. Sample cost values are illustrative, not live prices.</p></details>
        <details><summary>Is an APTron installation legally compliant or certified?</summary><p>Not automatically. The product targets industry technical controls including OWASP ASVS, NIST CSF and CIS Controls. APTron is responsible for secure software and security fixes; customers determine applicable data residency, privacy and operational obligations.</p></details>
        <details><summary>Why is activation blocked?</summary><p>Review readiness diagnostics and actual telemetry. Resolve missing evidence, unsupported collection methods or expired credentials before activation.</p></details>
        <details><summary>Why is my resource not visible?</summary><p>Check the explicit organization, environment filters, assigned permissions and fresh telemetry evidence. An empty authorized view does not mean a resource was deleted.</p></details>
        <details><summary>What should I include in a support report?</summary><p>Include resource ID, timestamp, application revision, expected and actual behavior, and redacted diagnostics. Never share passwords, secrets, customer payloads or cloud billing credentials.</p></details>
      </>}
    </section>
  </div>, document.body);
}
