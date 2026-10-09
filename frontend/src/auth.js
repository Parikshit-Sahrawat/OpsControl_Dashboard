const KEY = "opscontrol.sessionToken";
export const readToken = () => {
  try { return sessionStorage.getItem(KEY); } catch { return null; }
};
export const storeToken = token => { sessionStorage.setItem(KEY, token); };
export const clearToken = () => { try { sessionStorage.removeItem(KEY); } catch {} };
export const authHeaders = () => {
  const token = readToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
};
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
export async function signIn(username, password) {
  const response = await fetch(API_BASE + "/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error("Invalid username or password");
  const body = await response.json();
  storeToken(body.access_token);
  return body;
}
export async function sessionUser() {
  const response = await fetch(API_BASE + "/api/v1/auth/me", { headers: authHeaders() });
  if (!response.ok) throw new Error("Session expired or access denied");
  return response.json();
}
export async function signOut() {
  try { await fetch(API_BASE + "/api/v1/auth/logout", { method: "POST", headers: authHeaders() }); }
  finally { clearToken(); }
}
