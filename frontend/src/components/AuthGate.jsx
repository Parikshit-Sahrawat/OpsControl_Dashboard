import { useEffect, useState } from "react";
import App from "../App";
import { sessionWasRejected } from "../sessionVerification";
import ThemeToggle from "./ThemeToggle";
import { readToken, sessionUser, signIn, signOut, clearToken } from "../auth";

export default function AuthGate() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(readToken()));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    const token = readToken();
    if (!token) return;
    let live = true;
    const controller = new AbortController();
    sessionUser(controller.signal).then(next => {
      if (live && readToken() === token) setUser(next);
    }).catch(error => {
      if (!live || readToken() !== token) return;
      if (sessionWasRejected(error)) clearToken();
      setUser(null); // Fail closed: an unverifiable session never renders App.
      setError(sessionWasRejected(error) ? "Session expired or access denied" : "Session verification unavailable. Reload to retry or sign in.");
    }).finally(() => { if (live) setLoading(false); });
    return () => { live = false; controller.abort(); };
  }, []);
  useEffect(() => {
    if (!user) return;
    let live=true,pending=false;
    const refresh=async()=>{if(pending)return;pending=true;const token=readToken();
      try{const next=await sessionUser();if(live&&readToken()===token)setUser(current=>current?.authorization_revision===next.authorization_revision?current:next);}
      catch(error) {if(live&&readToken()===token){if(sessionWasRejected(error))clearToken();setUser(null);setError("Session could not be verified. Reload to retry or sign in.");}}
      finally{pending=false;}
    };
    const timer=setInterval(refresh,5000);window.addEventListener("focus",refresh);
    return()=>{live=false;clearInterval(timer);window.removeEventListener("focus",refresh);};
  },[user?.id]);
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
  if (user) return <><a className="skip-link" href="#main-content" onClick={(event) => {
    event.preventDefault();
    document.getElementById("main-content")?.focus();
  }}>Skip to main content</a><div className="session-banner"><span>Signed in as <b>{user.username}</b> {user.platform_admin ? "(Platform administrator)" : ""}</span><button onClick={logout}>Sign out</button></div><App key={user.id} user={user} /></>;
  return <main className="login-layout"><div className="login-appearance"><ThemeToggle /></div><form className="login-card" onSubmit={submit}>
    <span className="login-eyebrow">MONITORING WORKSPACE</span>
    <h1>OpsControl</h1><p>Sign in to view your authorized monitoring resources.</p>
    <label>Username<input type="text" name="username" required autoComplete="username" maxLength={120}/></label>
    <label>Password<input type="password" name="password" required autoComplete="current-password"/></label>
    {error && <div role="alert" className="error-box">{error}</div>}
    <button className="primary-button" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
    <small>First time? An administrator must be created using the documented local bootstrap command.</small>
  </form></main>;
}
