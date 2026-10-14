const KEY = "opscontrol.theme";
const valid = value => value === "dark" || value === "light";
const systemTheme = () => window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
let explicitPreference = false;

export function getTheme() {
  return document.documentElement.dataset.theme || "dark";
}

function applyTheme(value) {
  document.documentElement.dataset.theme = value;
  document.documentElement.style.colorScheme = value;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", value === "dark" ? "#09090b" : "#f8fafc");
}

export function initializeTheme() {
  let saved;
  try { saved = window.localStorage.getItem(KEY); } catch { /* Preferences remain usable without storage. */ }
  explicitPreference = valid(saved);
  applyTheme(valid(saved) ? saved : systemTheme());
}

export function setTheme(value) {
  if (!valid(value)) return;
  explicitPreference = true;
  applyTheme(value);
  try { window.localStorage.setItem(KEY, value); } catch { /* Theme still updates immediately. */ }
  window.dispatchEvent(new Event("opscontrol:theme"));
}

export function subscribeTheme(callback) {
  const storage = event => {
    if (event.key === KEY || event.key === null) {
      explicitPreference = valid(event.newValue);
      applyTheme(valid(event.newValue) ? event.newValue : systemTheme());
      callback();
    }
  };
  window.addEventListener("opscontrol:theme", callback);
  window.addEventListener("storage", storage);
  return () => {
    window.removeEventListener("opscontrol:theme", callback);
    window.removeEventListener("storage", storage);
  };
}

initializeTheme();
window.matchMedia?.("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (!explicitPreference) {
    applyTheme(systemTheme());
    window.dispatchEvent(new Event("opscontrol:theme"));
  }
});
