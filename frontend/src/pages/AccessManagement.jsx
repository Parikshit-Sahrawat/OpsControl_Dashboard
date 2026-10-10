import { useCallback, useEffect, useState } from "react";
import { authHeaders } from "../auth";

const BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
async function api(path, options = {}) {
  const response = await fetch(BASE + "/api/v1/auth" + path, {
    ...options,
    headers: { "Content-Type": "application/json", ...authHeaders(), ...(options.headers || {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "Request failed");
  }
  return response.status === 204 ? null : response.json();
}
const roleOptions = ["viewer", "operator", "org_admin"];

export default function AccessManagement() {
  const [users, setUsers] = useState([]);
  const [memberships, setMemberships] = useState([]);
  const [organizations, setOrganizations] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    const [people, assigned, orgs] = await Promise.all([
      api("/users"),
      api("/memberships"),
      fetch(BASE + "/api/v1/organizations", { headers: authHeaders() })
        .then(async r => { if (!r.ok) throw new Error("Could not load organizations"); return r.json(); }),
    ]);
    setUsers(people); setMemberships(assigned); setOrganizations(orgs);
  }, []);
  useEffect(() => { reload().catch(e => setError(e.message)); }, [reload]);

  async function act(action, message) {
    setError(""); setNotice(""); setBusy(true);
    try { await action(); await reload(); setNotice(message); }
    catch (err) { setError(err.message || "Action failed"); }
    finally { setBusy(false); }
  }

  function createUser(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const payload = { username: String(values.get("username")).trim(),
      password: String(values.get("password")),
      platform_admin: values.get("platform_admin") === "on" };
    act(() => api("/users", { method: "POST", body: JSON.stringify(payload) }), "User created. Assign a membership before they can see organizational data.");
    form.reset();
  }

  function addMembership(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const values = new FormData(form);
    const payload = { user_id: values.get("user_id"), organization_id: values.get("organization_id"), role: values.get("role") };
    act(() => api("/memberships", { method: "POST", body: JSON.stringify(payload) }), "Membership assigned. Prior sessions revoked.");
  }

  function updateRole(row, role) {
    act(() => api("/memberships/" + row.id, { method: "PATCH", body: JSON.stringify({ role }) }),
        "Role updated and user's sessions revoked.");
  }
  function removeRole(row) {
    if (!window.confirm("Remove this membership and revoke user sessions?")) return;
    act(() => api("/memberships/" + row.id, { method: "DELETE" }),
        "Membership removed and sessions revoked.");
  }
  function toggleStatus(user) {
    if (!window.confirm((user.active ? "Disable" : "Enable") + " this user and revoke sessions?")) return;
    act(() => api("/users/" + user.id + "/status", { method: "PATCH", body: JSON.stringify({ active: !user.active }) }),
        "User status updated and sessions revoked.");
  }
  function resetPassword(user) {
    const password = window.prompt("Enter a new password (minimum 12 characters). Do not use a shared or default password.");
    if (password === null) return;
    act(() => api("/users/" + user.id + "/password", { method: "POST", body: JSON.stringify({ new_password: password }) }),
        "Password updated. All existing user sessions revoked.");
  }

  return <div className="access-page">
    <div className="page-heading"><div><h1>Access Management</h1><p>Platform administrator · users, organizations and memberships</p></div></div>
    {error && <div className="error-box" role="alert">{error}</div>}
    {notice && <div className="source-fact" role="status">{notice}</div>}
    <div className="access-management-grid">
      <form className="card access-form" onSubmit={createUser}>
        <h2>Create user</h2>
        <label>Username<input name="username" autoComplete="off" minLength={1} maxLength={120} required /></label>
        <label>Initial password<input name="password" type="password" autoComplete="new-password" minLength={12} maxLength={1024} required /></label>
        <label className="access-checkbox"><input name="platform_admin" type="checkbox" /> Platform administrator</label>
        <button type="submit" className="primary-button" disabled={busy}>Create user</button>
      </form>
      <form className="card access-form" onSubmit={addMembership}>
        <h2>Assign organization membership</h2>
        <label>User<select name="user_id" required>{users.map(u => <option value={u.id} key={u.id}>{u.username}</option>)}</select></label>
        <label>Organization<select name="organization_id" required>{organizations.map(o => <option value={o.id} key={o.id}>{o.name}</option>)}</select></label>
        <label>Role<select name="role">{roleOptions.map(r => <option key={r}>{r}</option>)}</select></label>
        <button type="submit" className="primary-button" disabled={busy || !users.length || !organizations.length}>Assign membership</button>
      </form>
    </div>
    <section className="card access-table">
      <h2>Users</h2>
      <div className="table-wrap"><table><thead><tr><th>User</th><th>Type</th><th>Status</th><th>Actions</th></tr></thead>
        <tbody>{users.map(u => <tr key={u.id}><td>{u.username}</td><td>{u.platform_admin ? "Platform admin" : "Organization member"}</td>
          <td>{u.active ? "Active" : "Disabled"}</td><td className="access-actions">
            <button disabled={busy} className="filter-button" onClick={() => toggleStatus(u)}>{u.active ? "Disable" : "Enable"}</button>
            <button disabled={busy} className="filter-button" onClick={() => resetPassword(u)}>Reset password</button>
          </td></tr>)}</tbody></table></div>
    </section>
    <section className="card access-table">
      <h2>Organization memberships</h2>
      <div className="table-wrap"><table><thead><tr><th>User</th><th>Organization</th><th>Role</th><th>Actions</th></tr></thead>
        <tbody>{memberships.map(m => <tr key={m.id}><td>{users.find(u => u.id === m.user_id)?.username || m.user_id}</td>
          <td>{organizations.find(o => o.id === m.organization_id)?.name || m.organization_id}</td>
          <td><select disabled={busy} aria-label="Membership role" value={m.role} onChange={e => updateRole(m, e.target.value)}>
            {roleOptions.map(r => <option key={r} value={r}>{r}</option>)}</select></td>
          <td><button className="danger-button" disabled={busy} onClick={() => removeRole(m)}>Remove</button></td>
        </tr>)}</tbody></table></div>
    </section>
  </div>;
}
