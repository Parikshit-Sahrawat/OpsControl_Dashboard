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
  const [revision, setRevision] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const generation = useRef(0);
  const selection = useRef(0);
  const canManage = hasPermission(user, "templates.manage", organizationId);
  const base = `/api/v1/monitoring/data-sources/${sourceId}`;
  const call = (path, method = "GET", body) => control(path, method, body, { customerIds: [organizationId] });

  const load = async () => {
    const ticket = ++generation.current;
    setBusy(true); setError("");
    try {
      const [catalogue, attached, resolved] = await Promise.all([
        call("/api/v1/monitoring/templates"), call(base + "/templates"), call(base + "/effective-configuration"),
      ]);
      if (generation.current !== ticket) return;
      setTemplates(catalogue); setAttachments(attached); setEffective(resolved);
    } catch (e) { if (generation.current === ticket) setError(e.message); }
    finally { if (generation.current === ticket) setBusy(false); }
  };
  useEffect(() => {
    setSelected(""); setVersions([]); setVersion(""); setOverrides("{}"); setRevision(null);
    setTemplates([]); setAttachments([]); setEffective(null); load();
    return () => { generation.current++; selection.current++; };
    // load/call intentionally capture the exact scope for this generation.
  }, [sourceId, organizationId, user.authorization_revision]);

  const choose = async (id) => {
    const ticket = ++selection.current;
    setSelected(id); setVersions([]); setVersion(""); setError("");
    const existing = attachments.find(a => a.template_id === id);
    setRevision(existing?.updated_at || null);
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
      const existing = attachments.find(a => a.template_id === selected);
      const payload = { template_version: Number(version), overrides: parsed };
      await call(base + "/templates" + (existing ? `/${selected}` : ""), existing ? "PATCH" : "POST",
        existing ? { ...payload, expected_updated_at: revision } : { ...payload, template_id: selected });
      if (generation.current !== ticket) return;
      setSelected(""); setVersion(""); setVersions([]); setOverrides("{}");
      await load();
    } catch (e) { if (generation.current === ticket) { setError(e.message); setBusy(false); } }
  };
  return <section aria-label="Monitoring template configuration" className="card">
    <h3>Monitoring template configuration</h3>
    <p>Explicit committed version pins and validated package overrides. Saved configuration is not monitoring activation or healthy telemetry. Provider compatibility is unverified. Historical attachment revisions are not available.</p>
    {busy && <p role="status">Loading or saving template configuration…</p>}
    {error && <p role="alert">{error}</p>}
    <ul>{attachments.map(a => <li key={a.id}>
      {templates.find(t => t.id === a.template_id)?.name || a.template_id} · pinned v{a.template_version} · {a.enabled ? "Configuration enabled" : "Configuration disabled"}
      {canManage && <button type="button" disabled={busy} onClick={() => choose(a.template_id)}>Edit template pin</button>}
    </li>)}</ul>
    {!busy && !attachments.length && <p>No monitoring template attached.</p>}
    {canManage && <>
      <label className="form-field"><span>Monitoring template</span><select aria-label="Monitoring template" value={selected} disabled={busy} onChange={e => choose(e.target.value)}>
        <option value="">Select a committed template</option>
        {templates.filter(t => t.status === "COMMITTED").map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select></label>
      {selected && <>
        <label className="form-field"><span>Pinned template version</span><select aria-label="Pinned template version" value={version} disabled={busy || loadingVersions} onChange={e => setVersion(e.target.value)}>
          {versions.map(v => <option key={v.id} value={v.version}>v{v.version}</option>)}
        </select></label>
        <label className="form-field"><span>Template package overrides (JSON)</span><textarea aria-label="Template package overrides (JSON)" rows={5} value={overrides} onChange={e => setOverrides(e.target.value)} aria-invalid={!!error} /></label>
        <button type="button" disabled={busy || loadingVersions || !version} onClick={save}>Save template configuration</button>
      </>}
    </>}
    {effective && <p role="status">Configuration: {effective.valid ? "VALID" : "INCOMPLETE"}. Missing required attributes: {(effective.missing_required_attributes || []).join(", ") || "none"}. Activation and operational health require independent evidence.</p>}
  </section>;
}
