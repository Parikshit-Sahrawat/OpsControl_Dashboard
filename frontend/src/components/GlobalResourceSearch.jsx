import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { control } from "../controlPlane";
import { hasPermission } from "../permissions";
import useDialogFocus from "./useDialogFocus";
export default function GlobalResourceSearch({ user, organizationIds, environment, onSelect }) {
  const [open, setOpen] = useState(false), [query, setQuery] = useState(""), [results, setResults] = useState(null), [error, setError] = useState("");
  const input = useRef(null), dialog = useRef(null), opener = useRef(null), generation = useRef(0);
  const scope = organizationIds.join(","), env = JSON.stringify(environment);
  const allowed = hasPermission(user, "resources.view");
  const close = () => { setOpen(false); opener.current?.focus(); };
  useDialogFocus(dialog, open, close);
  useEffect(() => {
    const shortcut = e => { if (allowed && (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setOpen(true); } };
    window.addEventListener("keydown", shortcut); return () => window.removeEventListener("keydown", shortcut);
  }, [allowed]);
  useEffect(() => { setQuery(""); setResults(null); setError(""); setOpen(false); generation.current++; }, [scope, env, user.id, user.authorization_revision]);
  useEffect(() => { if (open) input.current?.focus(); }, [open]);
  useEffect(() => {
    const ticket = ++generation.current, controller = new AbortController();
    setResults(null); setError("");
    if (!open || !allowed || query.trim().length < 2 || !organizationIds.length) return;
    const timer = setTimeout(async () => {
      const params = new URLSearchParams({ search: query.trim(), limit: "8" });
      organizationIds.forEach(id => params.append("organization_id", id));
      (Array.isArray(environment) ? environment : environment ? [environment] : []).forEach(v => params.append("environments", v));
      try { const data = await control("/api/v1/unified/resources?" + params, "GET", undefined, { signal: controller.signal, customerIds: organizationIds }); if (ticket === generation.current) setResults(data); }
      catch (e) { if (ticket === generation.current && e.name !== "AbortError") setError(e.message); }
    }, 250);
    return () => { clearTimeout(timer); controller.abort(); generation.current++; };
    // Scope and environment keys are stable snapshots for request cancellation.
  }, [open, query, scope, env, allowed, user.authorization_revision]);
  const choose = item => { close(); onSelect(item); };
  if (!allowed) return null;
  return <>
    <button type="button" ref={opener} className="global-search-trigger" onClick={() => setOpen(true)} aria-label="Search authorized resources"><span>⌕ Search resources…</span><kbd>Ctrl K</kbd></button>
    {open && createPortal(<div className="modal-backdrop"><section ref={dialog} className="global-search-dialog card" role="dialog" aria-modal="true" aria-label="Find a resource">
      <div className="workspace-filter-heading"><h2>Find a resource</h2><button type="button" onClick={close} aria-label="Close resource search">×</button></div>
      <label className="form-field"><span>Search resource names</span><input ref={input} type="search" maxLength={200} aria-label="Global resource query" value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => { if (e.key === "Enter" && results?.items.length === 1) { e.preventDefault(); e.stopPropagation(); choose(results.items[0]); } }} /></label>
      <p className="muted">Search uses your selected operational organizations and environment. Resource inventory also has explicit customer filters.</p>
      {!organizationIds.length && <p role="status">Select an authorized organization before searching.</p>}
      {query.trim().length < 2 && <p role="status">Enter at least two characters.</p>}
      {query.trim().length >= 2 && !results && !error && organizationIds.length > 0 && <p role="status">Searching authorized resources…</p>}
      {error && <p role="alert">{error}</p>}
      {results && <><p role="status">{results.total} matches · showing up to 8</p><ul className="global-search-results">{results.items.map(item => <li key={item.id}><button type="button" onClick={() => choose(item)}><b>{item.name}</b><span>{item.domain} · {item.environment} · {item.inherited?.customer || "Authorized customer"}</span></button></li>)}</ul>{!results.items.length && <p>No authorized resources match. Try a different resource name.</p>}</>}
    </section></div>, document.body)}
  </>;
}
