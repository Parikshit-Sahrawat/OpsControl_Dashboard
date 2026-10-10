import { useEffect, useState } from "react";
import App from "../App";
import { readToken, sessionUser, signIn, signOut, clearToken } from "../auth";

export default function AuthGate() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(readToken()));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!readToken()) return;
    sessionUser().then(setUser).catch(() => { clearToken(); setUser(null); }).finally(() => setLoading(false));
  }, []);
  async function submit(event) {
    event.preventDefault();
    setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try { await signIn(String(data.get("username")), String(data.get("password"))); setUser(await sessionUser()); }
    catch (err) { clearToken(); setError(err.message || "Unable to sign in"); }
    finally { setBusy(false); }
  }
  async function logout() { await signOut(); setUser(null); }
  if (loading) return <main className="login-layout"><p>Checking session…</p></main>;
  if (user) return <><div className="session-banner"><span>Signed in as <b>{user.username}</b> {user.platform_admin ? "(Platform administrator)" : ""}</span><button onClick={logout}>Sign out</button></div><App user={user} /></>;
  return <main className="login-layout"><form className="login-card" onSubmit={submit}>
    <h1>OpsControl</h1><p>Sign in to view your authorized monitoring resources.</p>
    <label>Username<input type="text" name="username" required autoComplete="username" maxLength={120}/></label>
    <label>Password<input type="password" name="password" required autoComplete="current-password"/></label>
    {error && <div role="alert" className="error-box">{error}</div>}
    <button className="primary-button" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    <small>First time? An administrator must be created using the documented local bootstrap command.</small>
  </form></main>;
}
