const KEY = "opscontrol.theme";
const valid = value => value === "dark" || value === "light";

export function getTheme() {
  return document.documentElement.dataset.theme || "light";
}

function applyTheme(value) {
  document.documentElement.dataset.theme = value;
  document.documentElement.style.colorScheme = value;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", value === "dark" ? "#0b1020" : "#f3f5fb");
}

export function initializeTheme() {
  let saved;
  try { saved = window.localStorage.getItem(KEY); } catch { /* Preferences remain usable without storage. */ }
  applyTheme(valid(saved) ? saved : "light");
}

export function setTheme(value) {
  if (!valid(value)) return;
  applyTheme(value);
  try { window.localStorage.setItem(KEY, value); } catch { /* Theme still updates immediately. */ }
  window.dispatchEvent(new Event("opscontrol:theme"));
}

export function subscribeTheme(callback) {
  const storage = event => {
    if (event.key === KEY || event.key === null) {
      applyTheme(valid(event.newValue) ? event.newValue : "light");
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
