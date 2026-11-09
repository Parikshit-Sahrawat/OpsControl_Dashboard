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
  const [nextBefore, setNextBefore] = useState(null);
  const [revisionDetail, setRevisionDetail] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [draftPreview, setDraftPreview] = useState(null);
  const [conflict, setConflict] = useState(false);
  const [detaching, setDetaching] = useState(null);
  const pendingTransition = useRef(null);
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
        call("/api/v1/monitoring/templates"), call(base + "/templates"), call(base + "/effective-configuration"), call(base + "/configuration"), call(base + "/configuration/history?limit=10"),
      ]);
      if (generation.current !== ticket) return;
      setTemplates(catalogue); setAttachments(attached); setEffective(resolved); setHead(current); setHistory(revisions.items); setNextBefore(revisions.next_before); setRevisionDetail(null); setComparison(null); setDraftPreview(null); setConflict(false);
    } catch (e) { if (generation.current === ticket) setError(e.message); }
    finally { if (generation.current === ticket) setBusy(false); }
  };
  useEffect(() => {
    setSelected(""); setVersions([]); setVersion(""); setOverrides("{}");
    setTemplates([]); setAttachments([]); setEffective(null); setHead(null); setHistory([]); setNextBefore(null); setRevisionDetail(null); setComparison(null); setDraftPreview(null); setConflict(false); commandKey.current = null; pendingTransition.current = null; setDetaching(null); load();
    return () => { generation.current++; selection.current++; };
    // load/call intentionally capture the exact scope for this generation.
  }, [sourceId, organizationId, user.authorization_revision]);

  const choose = async (id) => {
    const ticket = ++selection.current; commandKey.current = null;
    setDraftPreview(null); setSelected(id); setVersions([]); setVersion(""); setError("");
    const existing = attachments.find(a => a.template_id === id);
    setOverrides(JSON.stringify(existing?.overrides || {}, null, 2));
    if (!id) { setLoadingVersions(false); return; }
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
  const desiredCommand = () => {
    let parsed;
    try { parsed = JSON.parse(overrides); }
    catch { throw new Error("Overrides: enter a valid JSON object."); }
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") throw new Error("Overrides: enter a JSON object, not a list or scalar.");
    const desired = attachments.map(a => ({template_id:a.template_id, template_version:a.template_version, priority:a.priority, enabled:a.enabled, overrides:a.overrides || {}}));
    const existing = desired.find(a => a.template_id === selected);
    if (existing) { existing.template_version = Number(version); existing.overrides = parsed; }
    else desired.push({template_id:selected, template_version:Number(version), priority:Math.max(0,...desired.map(a=>a.priority))+100, enabled:true, overrides:parsed});
    return {expected_revision:head.revision, attachments:desired};
  };
  const save = async () => {
    const ticket = generation.current;
    setError("");
    let payload;
    try { payload = desiredCommand(); } catch(e) { setError(e.message); return; }
    setBusy(true);
    try {
      commandKey.current ||= window.crypto.randomUUID();
      await call(base + "/configuration/commands", "POST", payload, {"Idempotency-Key":commandKey.current});
      if (generation.current !== ticket) return;
      commandKey.current = null;
      setSelected(""); setVersion(""); setVersions([]); setOverrides("{}");
      await load();
    } catch(e) { if (generation.current === ticket) {setError(e.message); setConflict(e.status === 409); setBusy(false);} }
  };
  const preview = async () => {
    const ticket = generation.current;
    setError(""); setDraftPreview(null);
    try {
      const payload = desiredCommand();
      setBusy(true);
      const result = await call(base + "/configuration/preview", "POST", payload);
      if (generation.current === ticket) setDraftPreview(result);
    } catch(e) { if (generation.current === ticket) { setError(e.message); setConflict(e.status === 409); } }
    finally { if (generation.current === ticket) setBusy(false); }
  };
  const inspectHistory = async (number, diff = false) => {
    const ticket = generation.current;
    setBusy(true); setError("");
    try {
      const result = await call(base + (diff ? `/configuration/diff?from_revision=${number}&to_revision=${head.revision}` : `/configuration/revisions/${number}`));
      if (generation.current === ticket) { if(diff) setComparison(result); else setRevisionDetail(result); }
    } catch(e) { if(generation.current === ticket) setError(e.message); }
    finally { if(generation.current === ticket) setBusy(false); }
  };
  const olderHistory = async () => {
    const ticket = generation.current;
    setBusy(true); setError("");
    try {
      const result = await call(base + `/configuration/history?limit=10&before=${nextBefore}`);
      if (generation.current === ticket) { setHistory(h=>[...h,...result.items.filter(r=>!h.some(old=>old.revision===r.revision))]); setNextBefore(result.next_before); }
    } catch(e) {if(generation.current === ticket) setError(e.message);}
    finally {if(generation.current === ticket) setBusy(false);}
  };
  const transition = async (path, payload) => {
    const ticket = generation.current;
    setBusy(true); setError("");
    try {
      const identity = JSON.stringify({path,payload});
      if (pendingTransition.current?.identity !== identity) pendingTransition.current = {identity,key:window.crypto.randomUUID()};
      await call(base + "/configuration/" + path, "POST", payload, { "Idempotency-Key": pendingTransition.current.key });
      if (ticket === generation.current) { pendingTransition.current = null; setDetaching(null); await load(); }
    } catch(e) { if (ticket === generation.current) { setError(e.message); setConflict(e.status === 409); setBusy(false); } }
  };
  return <section aria-label="Monitoring template configuration" className="card">
    <h3>Monitoring template configuration</h3>
    <p>Explicit committed version pins and validated package overrides. Saved configuration is not monitoring activation or healthy telemetry. Provider compatibility requires explicit applicability and independent evidence. Each committed configuration has immutable source-owned history.</p>
    {busy && <p role="status">Loading or saving template configuration…</p>}
    {error && <p role="alert">{error}</p>}
    {conflict && <div role="status">Another writer changed this source. Your staged edits are retained. Review the current revision before explicitly retrying; no automatic overwrite.
      <button type="button" disabled={busy} onClick={() => {commandKey.current=null; pendingTransition.current=null; load();}}>Refresh current revision and retain staged input</button>
    </div>}
    <ul>{attachments.map(a => <li key={a.id}>
      {templates.find(t => t.id === a.template_id)?.name || a.template_id} · pinned v{a.template_version} · {a.enabled ? "Configuration enabled" : "Configuration disabled"}
      {canManage && <><button type="button" disabled={busy} onClick={() => choose(a.template_id)}>Edit template pin</button>
      <button type="button" disabled={busy || head?.legacy_import_required} onClick={()=>setDetaching(a.template_id)}>Review detach {templates.find(t=>t.id===a.template_id)?.name || "template"}</button>
      {detaching===a.template_id && <div role="group" aria-label="Confirm template detachment"><p>Detach creates a new audited revision. History is retained; this does not stop or activate a collector.</p><button type="button" disabled={busy} onClick={()=>transition("commands",{expected_revision:head.revision,attachments:attachments.filter(x=>x.template_id!==a.template_id).map(({template_id,template_version,priority,enabled,overrides})=>({template_id,template_version,priority,enabled,overrides:overrides || {}}))})}>Confirm detach template</button><button type="button" onClick={()=>setDetaching(null)}>Cancel detachment</button></div>}</>}
    </li>)}</ul>
    {!busy && !attachments.length && <p>No monitoring template attached.</p>}
    {canManage && head?.legacy_import_required && <button type="button" disabled={busy} onClick={() => transition("import-legacy", { expected_revision: 0 })}>Preserve legacy configuration history</button>}
    {canManage && !head?.legacy_import_required && <>
      <label className="form-field"><span>Monitoring template</span><select aria-label="Monitoring template" value={selected} disabled={busy} onChange={e => choose(e.target.value)}>
        <option value="">Select a committed template</option>
        {templates.filter(t => t.status === "COMMITTED").map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
      </select></label>
      {selected && <>
        <label className="form-field"><span>Pinned template version</span><select aria-label="Pinned template version" value={version} disabled={busy || loadingVersions} onChange={e => { setVersion(e.target.value); setDraftPreview(null); commandKey.current = null; }}>
          {versions.map(v => <option key={v.id} value={v.version}>v{v.version}</option>)}
        </select></label>
        <label className="form-field"><span>Template package overrides (JSON)</span><textarea aria-label="Template package overrides (JSON)" rows={5} value={overrides} onChange={e => { setOverrides(e.target.value); setDraftPreview(null); commandKey.current = null; }} aria-invalid={!!error} /></label>
        <p role="status">Staged draft — browser memory only, not applied or activated. Leaving this workspace discards it.</p>
        <button type="button" disabled={busy || loadingVersions || !version} onClick={preview}>Validate staged draft</button>
        <button type="button" disabled={busy || loadingVersions || !version} onClick={save}>Save template configuration</button>
        <button type="button" disabled={busy} onClick={()=>{setSelected("");setVersion("");setOverrides("{}");setDraftPreview(null);commandKey.current=null;}}>Discard staged changes</button>
        {draftPreview && <section aria-label="Staged configuration preview"><p>Backend validation: {draftPreview.validation.valid ? "VALID" : "BLOCKED"}. Application NOT REQUESTED; health UNVERIFIED.</p><pre>{JSON.stringify(draftPreview,null,2)}</pre></section>}
      </>}
    </>}
    <section aria-label="Configuration revision history"><h4>Configuration history · revision {head?.revision ?? "unknown"}</h4>
      {!history.length && <p>No revision has been committed. Legacy records remain preserved.</p>}
      <ol>{history.map(h => <li key={h.revision}>Revision {h.revision} · {h.kind} · {h.actor} · {new Date(h.created_at).toLocaleString()} · {h.content_hash.slice(0,12)}
        <button type="button" disabled={busy} onClick={()=>inspectHistory(h.revision)}>View revision {h.revision}</button>
        <button type="button" disabled={busy} onClick={()=>inspectHistory(h.revision,true)}>Compare revision {h.revision} to current</button>
        {canManage && h.kind !== "IMPORT" && h.revision !== head?.revision && <button type="button" disabled={busy} onClick={() => transition("rollback", { expected_revision: head.revision, target_revision: h.revision })}>Restore revision {h.revision} as new configuration</button>}
      </li>)}</ol>
      {nextBefore && <button type="button" disabled={busy} onClick={olderHistory}>Load older configuration history</button>}
      {revisionDetail && <section aria-label="Configuration revision detail"><pre>{JSON.stringify(revisionDetail,null,2)}</pre><button type="button" onClick={()=>setRevisionDetail(null)}>Close revision detail</button></section>}
      {comparison && <section aria-label="Configuration revision comparison"><p>{comparison.changed ? "Configuration changed" : "No content difference"}</p><pre>{JSON.stringify(comparison,null,2)}</pre><button type="button" onClick={()=>setComparison(null)}>Close comparison</button></section>}
      <p>Restoration revalidates current compatibility and permissions. It never activates collectors or restores secrets/checkpoints.</p>
    </section>
    {effective && <><button type="button" onClick={() => setShowEffective(v=>!v)}>{showEffective ? "Hide" : "Preview"} saved effective configuration</button>{showEffective && <pre className="effective-config-preview" aria-label="Saved effective configuration">{JSON.stringify(effective,null,2)}</pre>}</>}
    {effective && <p role="status">Configuration: {!effective.templates?.length ? "NO TEMPLATE ATTACHED" : effective.valid ? "VALID" : "INCOMPLETE"}. Missing required attributes: {(effective.missing_required_attributes || []).join(", ") || "none"}. Activation and operational health require independent evidence.</p>}
  </section>;
}
