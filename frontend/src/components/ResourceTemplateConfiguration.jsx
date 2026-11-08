import { useEffect, useRef, useState } from "react";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";

// The existing source attachment is the only configuration owner. Saving here
// does not activate a collector or establish health/provider compatibility.
export default function ResourceTemplateConfiguration({ sourceId, organizationId, user }) {
  const [templates, setTemplates] = useState([]);
  const [attachments, setAttachments] = useState([]);
  const [effective, setEffective] = useState(null);
  const [selected, setSelected] = useState("");
  const [versions, setVersions] = useState([]);
  const [version, setVersion] = useState("");
  const [overrides, setOverrides] = useState("{}");
  const [head, setHead] = useState(null);
  const [history, setHistory] = useState([]);
  const commandKey = useRef(null);
  const [showEffective, setShowEffective] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const generation = useRef(0);
  const selection = useRef(0);
  const canManage = hasPermission(user, "templates.manage", organizationId);
  const base = `/api/v1/monitoring/data-sources/${sourceId}`;
  const call = (path, method = "GET", body, headers) => control(path, method, body, { customerIds: [organizationId], headers });

  const load = async () => {
    const ticket = ++generation.current;
    setBusy(true); setError("");
    try {
      const [catalogue, attached, resolved, current, revisions] = await Promise.all([
        call("/api/v1/monitoring/templates"), call(base + "/templates"), call(base + "/effective-configuration"), call(base + "/configuration"), call(base + "/configuration/history"),
      ]);
      if (generation.current !== ticket) return;
      setTemplates(catalogue); setAttachments(attached); setEffective(resolved); setHead(current); setHistory(revisions.items);
    } catch (e) { if (generation.current === ticket) setError(e.message); }
    finally { if (generation.current === ticket) setBusy(false); }
  };
  useEffect(() => {
    setSelected(""); setVersions([]); setVersion(""); setOverrides("{}");
    setTemplates([]); setAttachments([]); setEffective(null); setHead(null); setHistory([]); commandKey.current = null; load();
    return () => { generation.current++; selection.current++; };
    // load/call intentionally capture the exact scope for this generation.
  }, [sourceId, organizationId, user.authorization_revision]);

  const choose = async (id) => {
    const ticket = ++selection.current; commandKey.current = null;
    setSelected(id); setVersions([]); setVersion(""); setError("");
    const existing = attachments.find(a => a.template_id === id);
    setOverrides(JSON.stringify(existing?.overrides || {}, null, 2));
    if (!id) return;
    setLoadingVersions(true);
    try {
      const rows = await call(`/api/v1/monitoring/templates/${id}/versions`);
      if (selection.current !== ticket) return;
      const committed = rows.filter(v => v.status === "COMMITTED");
      setVersions(committed);
      setVersion(String(existing?.template_version || committed[0]?.version || ""));
    } catch (e) { if (selection.current === ticket) setError(e.message); }
    finally { if (selection.current === ticket) setLoadingVersions(false); }
  };
  const save = async () => {
    const ticket = generation.current;
    setError("");
    let parsed;
    try { parsed = JSON.parse(overrides); }
    catch { setError("Overrides: enter a valid JSON object."); return; }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      setError("Overrides: enter a JSON object, not a list or scalar."); return;
    }
    setBusy(true);
    try {
      const desired = attachments.map(a => ({ template_id: a.template_id, template_version: a.template_version, priority: a.priority, enabled: a.enabled, overrides: a.overrides || {} }));
      const existing = desired.find(a => a.template_id === selected);
      if (existing) { existing.template_version = Number(version); existing.overrides = parsed; }
      else desired.push({ template_id: selected, template_version: Number(version), priority: Math.max(0, ...desired.map(a => a.priority)) + 100, enabled: true, overrides: parsed });
      commandKey.current ||= window.crypto.randomUUID();
      await call(base + "/configuration/commands", "POST", { expected_revision: head.revision, attachments: desired }, { "Idempotency-Key": commandKey.current });
      commandKey.current = null;
      if (generation.current !== ticket) return;
      setSelected(""); setVersion(""); setVersions([]); setOverrides("{}");
      await load();
    } catch (e) { if (generation.current === ticket) { setError(e.message); setBusy(false); } }
  };
  const transition = async (path, payload) => {
    const ticket = generation.current;
    setBusy(true); setError("");
    try {
      await call(base + "/configuration/" + path, "POST", payload, { "Idempotency-Key": window.crypto.randomUUID() });
      if (ticket === generation.current) await load();
    } catch(e) { if (ticket === generation.current) { setError(e.message); setBusy(false); } }
  };
  return <section aria-label="Monitoring template configuration" className="card">
    <h3>Monitoring template configuration</h3>
    <p>Explicit committed version pins and validated package overrides. Saved configuration is not monitoring activation or healthy telemetry. Provider compatibility requires explicit applicability and independent evidence. Each committed configuration has immutable source-owned history.</p>
    {busy && <p role="status">Loading or saving template configuration…</p>}
    {error && <p role="alert">{error}</p>}
    <ul>{attachments.map(a => <li key={a.id}>
      {templates.find(t => t.id === a.template_id)?.name || a.template_id} · pinned v{a.template_version} · {a.enabled ? "Configuration enabled" : "Configuration disabled"}
      {canManage && <button type="button" disabled={busy} onClick={() => choose(a.template_id)}>Edit template pin</button>}
    </li>)}</ul>
    {!busy && !attachments.length && <p>No monitoring template attached.</p>}
    {canManage && head?.legacy_import_required && <button type="button" disabled={busy} onClick={() => transition("import-legacy", { expected_revision: 0 })}>Preserve legacy configuration history</button>}
    {canManage && !head?.legacy_import_required && <>
      <label className="form-field"><span>Monitoring template</span><select aria-label="Monitoring template" value={selected} disabled={busy} onChange={e => choose(e.target.value)}>
        <option value="">Select a committed template</option>
        {templates.filter(t => t.status === "COMMITTED").map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select></label>
      {selected && <>
        <label className="form-field"><span>Pinned template version</span><select aria-label="Pinned template version" value={version} disabled={busy || loadingVersions} onChange={e => { setVersion(e.target.value); commandKey.current = null; }}>
          {versions.map(v => <option key={v.id} value={v.version}>v{v.version}</option>)}
        </select></label>
        <label className="form-field"><span>Template package overrides (JSON)</span><textarea aria-label="Template package overrides (JSON)" rows={5} value={overrides} onChange={e => { setOverrides(e.target.value); commandKey.current = null; }} aria-invalid={!!error} /></label>
        <button type="button" disabled={busy || loadingVersions || !version} onClick={save}>Save template configuration</button>
      </>}
    </>}
    <section aria-label="Configuration revision history"><h4>Configuration history · revision {head?.revision ?? "unknown"}</h4>
      {!history.length && <p>No revision has been committed. Legacy records remain preserved.</p>}
      <ol>{history.map(h => <li key={h.revision}>Revision {h.revision} · {h.kind} · {h.actor} · {new Date(h.created_at).toLocaleString()} · {h.content_hash.slice(0,12)}
        {canManage && h.kind !== "IMPORT" && h.revision !== head?.revision && <button type="button" disabled={busy} onClick={() => transition("rollback", { expected_revision: head.revision, target_revision: h.revision })}>Restore revision {h.revision} as new configuration</button>}
      </li>)}</ol><p>Restoration revalidates current compatibility and permissions. It never activates collectors or restores secrets/checkpoints.</p>
    </section>
    {effective && <><button type="button" onClick={() => setShowEffective(v=>!v)}>{showEffective ? "Hide" : "Preview"} saved effective configuration</button>{showEffective && <pre className="effective-config-preview" aria-label="Saved effective configuration">{JSON.stringify(effective,null,2)}</pre>}</>}
    {effective && <p role="status">Configuration: {!effective.templates?.length ? "NO TEMPLATE ATTACHED" : effective.valid ? "VALID" : "INCOMPLETE"}. Missing required attributes: {(effective.missing_required_attributes || []).join(", ") || "none"}. Activation and operational health require independent evidence.</p>}
  </section>;
}
