import { useEffect, useState } from "react";
import { control } from "../controlPlane";
import { TemplateEditor } from "../pages/ResourceManagementV2";
export default function TemplateCatalog({ user }) {
  const [rows, setRows] = useState(null), [error, setError] = useState(""), [editor, setEditor] = useState(null), [revision, setRevision] = useState(0), [history, setHistory] = useState(null);
  useEffect(() => {
    let live = true; setRows(null); setError(""); setEditor(null); setHistory(null);
    control("/api/v1/monitoring/templates?limit=500").then(v => live && setRows(v)).catch(e => live && setError(e.message));
    return () => { live = false; };
  }, [revision, user.id, user.authorization_revision]);
  const versions = async row => { try { setError(""); setHistory({ name: row.name, versions: await control(`/api/v1/monitoring/templates/${row.id}/versions`) }); } catch(e) { setError(e.message); } };
  return <section className="template-catalog">
    <div className="page-heading"><div><h1>Monitoring Templates</h1><p>Shared policy packages. Attach explicit committed versions within an authorized resource.</p></div><div className="page-header-actions"><button type="button" onClick={() => setRevision(v => v + 1)}>Refresh templates</button><button type="button" className="primary-button" disabled={!user.platform_admin} title={!user.platform_admin ? "Package creation requires a platform administrator" : undefined} onClick={() => setEditor({})}>Create Template</button></div></div>
    {error && <p role="alert">{error}</p>}{!rows && !error && <p role="status">Loading template packages…</p>}
    <div className="workspace-card-grid">{rows?.map(row => <article className="card" key={row.id}><div className="workspace-filter-heading"><h2>{row.name}</h2><span className="status status--unknown">{row.status} · v{row.version}</span></div><p>{row.description || "No description"}</p><p className="muted">{row.scope}</p><div className="page-header-actions"><button type="button" onClick={() => versions(row)}>Package versions</button>{user.platform_admin && <button type="button" onClick={() => setEditor(row)}>Edit package</button>}</div></article>)}</div>
    {rows?.length === 0 && <p>No template packages are available.</p>}
    {history && <section className="card" aria-label="Template package history"><div className="workspace-filter-heading"><h2>{history.name}: package versions</h2><button type="button" onClick={() => setHistory(null)}>Close package history</button></div><ul>{history.versions.map(v => <li key={v.id}>v{v.version} · {v.status} · {new Date(v.committed_at).toLocaleString()}</li>)}</ul><p className="muted">Package versions are retained. Source-owned attachment and override history is available within the resource configuration.</p></section>}
    {editor && <TemplateEditor value={editor} user={user} onClose={() => setEditor(null)} onSaved={() => { setEditor(null); setRevision(v => v + 1); }} />}
  </section>;
}
